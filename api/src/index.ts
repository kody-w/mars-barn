import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';
import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';
import { execFileSync } from 'child_process';

const ROOT = path.resolve(__dirname, '..', '..');
const dbPath = process.env.DATABASE_URL?.replace('file:', '') || path.join(__dirname, '..', 'dev.db');
const adapter = new PrismaBetterSqlite3({ url: dbPath });
const prisma = new PrismaClient({ adapter } as any);
const app = express();
const COLONY_JSON = path.join(ROOT, 'state', 'colony.json');

app.use(cors());
app.use(express.json());

// Get all colonies (for the dashboard)
app.get('/api/colonies', async (req, res) => {
    try {
        const colonies = await prisma.colony.findMany({
            orderBy: { createdAt: 'desc' }
            // In a real sophisticated query we'd pull events, but let's keep it simple for the dashboard feed right now
        });

        // Format for existing frontend
        const formatted = colonies.map((c) => ({
            id: c.name,
            status: c.status,
            age_sols: c.sol,
            last_event: "Nominal operations", // Awaiting full event table integration
            stats: {
                solar_efficiency: c.panelDustFactor,
                battery_reserves_kwh: c.storedEnergyKwh,
                supply_reserves_tons: c.foodReservesKg / 1000 // approx
            }
        }));

        res.json(formatted);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// Create a new colony (The Cradle)
app.post('/api/colonies', async (req, res) => {
    try {
        const { name, latitude, longitude, panelAreaM2, crewSize, ownerUtxo } = req.body;

        if (!name) return res.status(400).json({ error: "Colony name required" });

        const newColony = await prisma.colony.create({
            data: {
                ownerUtxo: ownerUtxo ?? `unowned:${Date.now()}`,
                name,
                latitude: latitude ?? -4.5,
                longitude: longitude ?? 137.4,
                panelAreaM2: panelAreaM2 ?? 400,
                crewSize: crewSize ?? 4,
                // Start out with default resources
                interiorTempK: 293.0,
                storedEnergyKwh: 500.0,
                foodReservesKg: 500.0,
                waterReservesL: 1000.0
            }
        });

        res.status(201).json(newColony);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// Force a tick — delegates to the real Python physics engine
app.post('/api/tick', async (_req, res) => {
    try {
        // Run the authoritative Python simulation (advances to current sol)
        const output = execFileSync('python3', ['src/live.py'], {
            cwd: ROOT,
            timeout: 30_000,
            encoding: 'utf-8',
        });

        // Read the updated state
        const colony = JSON.parse(fs.readFileSync(COLONY_JSON, 'utf-8'));

        res.json({
            success: true,
            sol: colony.sol,
            status: colony.habitat.interior_temp_k > 273.15 ? 'HABITABLE' : 'CRITICAL',
            output: output.trim(),
        });
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Project forward — Monte Carlo colony projection ─────────────────
app.post('/api/project', (_req, res) => {
    try {
        const sols = Math.min(200, Math.max(1, parseInt(_req.body?.sols) || 30));
        const runs = Math.min(50, Math.max(5, parseInt(_req.body?.runs) || 20));

        const output = execFileSync('python3', [
            'src/project.py', '--sols', String(sols), '--runs', String(runs), '--seed', '42', '--json'
        ], { cwd: ROOT, timeout: 120_000, encoding: 'utf-8' });

        const result = JSON.parse(output);
        res.json(result);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Single colony by ID ─────────────────────────────────────────────
app.get('/api/colonies/:id', async (req, res) => {
    try {
        const colony = await prisma.colony.findFirst({
            where: {
                OR: [
                    { id: req.params.id },
                    { name: req.params.id },
                ],
            },
            include: { events: true },
        });
        if (!colony) return res.status(404).json({ error: 'Colony not found' });
        res.json(colony);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Colony log entries (paginated) ──────────────────────────────────
app.get('/api/colonies/:id/log', async (req, res) => {
    try {
        const colony = await prisma.colony.findFirst({
            where: {
                OR: [
                    { id: req.params.id },
                    { name: req.params.id },
                ],
            },
        });
        if (!colony) return res.status(404).json({ error: 'Colony not found' });

        const page = Math.max(1, parseInt(req.query.page as string) || 1);
        const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string) || 50));

        const logs = await prisma.log.findMany({
            where: { colonyId: colony.id },
            orderBy: { sol: 'desc' },
            skip: (page - 1) * limit,
            take: limit,
        });
        const total = await prisma.log.count({ where: { colonyId: colony.id } });

        res.json({ logs, page, limit, total });
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Live colony state (from Python sim's colony.json) ───────────────
app.get('/api/live', (_req, res) => {
    try {
        if (!fs.existsSync(COLONY_JSON)) {
            return res.status(404).json({ error: 'No live colony state found' });
        }
        const data = JSON.parse(fs.readFileSync(COLONY_JSON, 'utf-8'));
        res.json(data);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Health check ────────────────────────────────────────────────────
app.get('/api/health', async (_req, res) => {
    try {
        await prisma.$queryRaw`SELECT 1`;
        res.json({ status: 'ok', uptime: process.uptime() });
    } catch (error) {
        res.status(503).json({ status: 'degraded', db: 'unreachable' });
    }
});

// ── Colony network — all parallel universes from state/*.json ───────
app.get('/api/network', (_req, res) => {
    try {
        const stateDir = path.join(ROOT, 'state');
        const files = fs.readdirSync(stateDir).filter(f => f.endsWith('.json') && f !== 'marsbarn-gpt.json');
        const colonies = files.map(f => {
            try {
                const data = JSON.parse(fs.readFileSync(path.join(stateDir, f), 'utf-8'));
                return {
                    file: f,
                    name: data.name ?? f.replace('.json', ''),
                    sol: data.sol ?? data.age_sols ?? 0,
                    status: data.status ?? (data.habitat ? 'ALIVE' : 'UNKNOWN'),
                    crew: data.crew ?? null,
                    location: data.location ?? null,
                };
            } catch (e) { console.warn(`Failed to parse state/${f}:`, e); return null; }
        }).filter(Boolean);

        res.json({ count: colonies.length, colonies });
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Multi-planet backtest ───────────────────────────────────────────
app.get('/api/multiplanet', (_req, res) => {
    try {
        const resultPath = path.join(ROOT, 'state', 'multiplanet-backtest.json');
        if (!fs.existsSync(resultPath)) {
            const sols = Math.min(669, Math.max(1, parseInt(_req.query.sols as string) || 669));
            execFileSync('python3', ['src/planetary_climate.py', String(sols)], {
                cwd: ROOT,
                timeout: 120_000,
            });
        }
        const data = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
        res.json(data);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Backtest results ────────────────────────────────────────────────
app.get('/api/backtest', (_req, res) => {
    try {
        const resultPath = path.join(ROOT, 'state', 'backtest.json');
        if (!fs.existsSync(resultPath)) {
            return res.status(404).json({ error: 'No backtest results. Run: python src/backtest.py' });
        }
        const data = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
        res.json(data);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Fork leaderboard ────────────────────────────────────────────────
app.get('/api/leaderboard', (_req, res) => {
    try {
        const resultPath = path.join(ROOT, 'state', 'leaderboard.json');
        if (!fs.existsSync(resultPath)) {
            // Generate it
            execFileSync('python3', ['src/leaderboard.py', '--output', 'state/leaderboard.json'], {
                cwd: ROOT,
                timeout: 60_000,
            });
        }
        const data = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
        res.json(data);
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Mars climate statistics ─────────────────────────────────────────
app.get('/api/climate', (_req, res) => {
    try {
        const output = execFileSync('python3', [
            '-c',
            'import sys; sys.path.insert(0, "src"); from mars_climate import annual_summary; import json; print(json.dumps(annual_summary()))'
        ], {
            cwd: ROOT,
            timeout: 10_000,
            encoding: 'utf-8',
        });
        res.json(JSON.parse(output));
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

// ── Rappter integration (stub — returns static/empty data) ──────────
app.get('/api/rappter', (req, res) => {
    const file = req.query.file as string;
    if (file === 'agents.json') return res.json([]);
    if (file === 'trending.json') return res.json({ topics: [], updated: new Date().toISOString() });
    res.json({});
});

// ── Engine status (stub) ────────────────────────────────────────────
app.get('/api/engine/status', (_req, res) => {
    res.json({ status: 'offline', message: 'Local engine not running' });
});

app.get('/api/engine/gateway', (_req, res) => {
    res.json({ connected: false, endpoint: null });
});

export { app, prisma };

const PORT = process.env.PORT || 3001;
if (require.main === module) {
    const server = app.listen(PORT, () => {
        console.log(`Mars Barn Engine running on port ${PORT}`);
    });

    const shutdown = async () => {
        server.close();
        await prisma.$disconnect();
        process.exit(0);
    };
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
}
