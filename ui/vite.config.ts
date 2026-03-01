import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/mars-barn/',
  server: {
    port: 5173,
    proxy: {
      '/api/colonies': {
        bypass: (req, res) => {
          if (req.url === '/api/colonies') {
            try {
              const dataPath = path.resolve(__dirname, '../data/state.json')
              if (fs.existsSync(dataPath)) {
                const state = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
                
                // Transform single state into array format expected by frontend
                const colony = {
                  id: "Alpha Base",
                  status: state.habitat.interior_temp_k > 200 ? 'ALIVE' : 'DEAD',
                  age_sols: state.sol,
                  last_event: state.active_events.length > 0 ? state.active_events[state.active_events.length-1].description : "Nominal operations",
                  stats: {
                    solar_efficiency: Math.max(0.1, 1.0 - (state.active_events.filter(e => e.type.startsWith('dust_')).length * 0.4)),
                    battery_reserves_kwh: state.habitat.stored_energy_kwh,
                    supply_reserves_tons: 15.0 - (state.sol * 0.05) // Fake burn rate for visual
                  }
                };
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify([colony]))
              } else {
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify([]))
              }
            } catch (err) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: err.message }))
            }
            return true // bypass standard proxying
          }
        }
      }
    }
  }
})
