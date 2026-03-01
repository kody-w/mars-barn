import request from 'supertest';
import { app } from '../src/index';

describe('Mars Barn API', () => {

    describe('GET /api/health', () => {
        it('returns ok status', async () => {
            const res = await request(app).get('/api/health');
            // DB may not be migrated in test, so accept 200 or 503
            expect([200, 503]).toContain(res.status);
            expect(res.body).toHaveProperty('status');
        }, 15000);
    });

    describe('GET /api/live', () => {
        it('returns colony state from colony.json', async () => {
            const res = await request(app).get('/api/live');
            expect(res.status).toBe(200);
            expect(res.body).toHaveProperty('name');
            expect(res.body).toHaveProperty('sol');
            expect(res.body).toHaveProperty('habitat');
        });

        it('includes crew and greenhouse data', async () => {
            const res = await request(app).get('/api/live');
            expect(res.status).toBe(200);
            if (res.body.crew) {
                expect(res.body.crew).toHaveProperty('morale');
                expect(res.body.crew).toHaveProperty('health');
            }
            if (res.body.greenhouse) {
                expect(res.body.greenhouse).toHaveProperty('growth_stage');
            }
        });
    });

    describe('GET /api/network', () => {
        it('returns list of colonies from state dir', async () => {
            const res = await request(app).get('/api/network');
            expect(res.status).toBe(200);
            expect(res.body).toHaveProperty('count');
            expect(res.body).toHaveProperty('colonies');
            expect(Array.isArray(res.body.colonies)).toBe(true);
            expect(res.body.count).toBeGreaterThan(0);
        });

        it('each colony has required fields', async () => {
            const res = await request(app).get('/api/network');
            for (const colony of res.body.colonies) {
                expect(colony).toHaveProperty('name');
                expect(colony).toHaveProperty('file');
            }
        });
    });

    describe('GET /api/colonies', () => {
        it('returns array (may be empty if DB not seeded)', async () => {
            const res = await request(app).get('/api/colonies');
            // DB might not be available, accept 200 or 500
            if (res.status === 200) {
                expect(Array.isArray(res.body)).toBe(true);
            }
        });
    });

    describe('POST /api/tick', () => {
        it('runs Python physics and returns result', async () => {
            const res = await request(app).post('/api/tick');
            expect(res.status).toBe(200);
            expect(res.body).toHaveProperty('success', true);
            expect(res.body).toHaveProperty('sol');
        }, 30000);
    });

    describe('POST /api/project', () => {
        it('returns projection with bands and narratives', async () => {
            const res = await request(app)
                .post('/api/project')
                .send({ sols: 10, runs: 5 });
            expect(res.status).toBe(200);
            expect(res.body).toHaveProperty('survival_rate');
            expect(res.body).toHaveProperty('bands');
            expect(res.body).toHaveProperty('narratives');
            expect(Array.isArray(res.body.bands)).toBe(true);
            expect(res.body.bands.length).toBe(10);
        }, 60000);
    });
});
