import express from 'express';
import cors from 'cors';
import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

const prisma = new PrismaClient();
const app = express();
const ROOT = path.resolve(__dirname, '..', '..');
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
        const output = execSync('python3 src/live.py', {
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
            } catch { return null; }
        }).filter(Boolean);

        res.json({ count: colonies.length, colonies });
    } catch (error) {
        const err = error as Error;
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Mars Barn Engine running on port ${PORT}`);
});
