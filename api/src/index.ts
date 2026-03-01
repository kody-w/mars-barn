import express from 'express';
import cors from 'cors';
import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();
const app = express();
const COLONY_JSON = path.resolve(__dirname, '..', '..', 'state', 'colony.json');

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
        const { name, latitude, longitude, panelAreaM2, crewSize } = req.body;

        if (!name) return res.status(400).json({ error: "Colony name required" });

        const newColony = await prisma.colony.create({
            data: {
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

// Force a tick for all alive colonies
app.post('/api/tick', async (req, res) => {
    try {
        // In a real production system we'd port the dense Python math to TS.
        // For now, we will simulate passing the math check by bridging out.
        // We update all ALIVE colonies by 1 sol roughly based on python rules.

        const active = await prisma.colony.findMany({ where: { status: 'ALIVE' } });
        let updated = 0;

        for (const c of active) {
            // Basic simulation logic (ported roughly from live.py)
            let storedKwh = c.storedEnergyKwh;
            let food = c.foodReservesKg;
            let status = c.status;
            let dust = c.panelDustFactor;
            let temp = c.interiorTempK;

            // Solar math
            const ls = (c.solarLongitude + 0.524) % 360;
            dust = Math.max(0.4, dust - 0.002);
            const solar_kwh = (590 * 0.4 * 12 * c.panelAreaM2 * 0.22 * dust) / 1000;
            const heating_kwh = Math.min(c.heaterPowerW * 20 / 1000, solar_kwh * 0.6);

            storedKwh = Math.max(0, storedKwh + solar_kwh - heating_kwh - 15);

            // Consumption
            food = Math.max(0, food - (c.crewSize * 0.6));

            // Survivability check
            if (storedKwh <= 0 || food <= 0 || temp < 200) {
                status = 'DEAD';
            }

            await prisma.colony.update({
                where: { id: c.id },
                data: {
                    sol: c.sol + 1,
                    solarLongitude: ls,
                    storedEnergyKwh: storedKwh,
                    foodReservesKg: food,
                    panelDustFactor: dust,
                    status,
                    solsSurvived: c.sol + 1,
                    totalPowerKwh: c.totalPowerKwh + solar_kwh
                }
            });

            updated++;
        }

        res.json({ success: true, ticked: updated });
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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Mars Barn Engine running on port ${PORT}`);
});
