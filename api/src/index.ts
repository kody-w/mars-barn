import express from 'express';
import cors from 'cors';
import { PrismaClient } from '@prisma/client';
import * as util from 'util';
import * as path from 'path';

const prisma = new PrismaClient();
const app = express();

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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Mars Barn Engine running on port ${PORT}`);
});
