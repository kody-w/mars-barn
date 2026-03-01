import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/mars-barn/',
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api/colonies': {
        target: 'http://localhost:5173', // dummy target to satisfy vite proxy check
        bypass: (req, res) => {
          if (req.url === '/api/colonies') {
            fetch('https://raw.githubusercontent.com/kody-w/mars-barn/main/state/colony.json')
              .then(r => r.json())
              .then((state: any) => {
                const colony = {
                  id: "Alpha Base",
                  status: state.habitat.interior_temp_k > 200 ? 'ALIVE' : 'DEAD',
                  age_sols: state.sol,
                  last_event: state.active_events.length > 0 ? state.active_events[state.active_events.length - 1].description : "Nominal operations",
                  stats: {
                    solar_efficiency: Math.max(0.1, 1.0 - (state.active_events.filter((e: any) => e.type.startsWith('dust_')).length * 0.4)),
                    battery_reserves_kwh: state.habitat.stored_energy_kwh,
                    supply_reserves_tons: 15.0 - (state.sol * 0.05)
                  }
                };
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify([colony]))
              })
              .catch((err: any) => {
                res.statusCode = 500
                res.end(JSON.stringify({ error: err.message }))
              });
            return false // bypass standard proxying
          }
        }
      }
    }
  }
})
