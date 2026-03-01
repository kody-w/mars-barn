import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Create a local virtual API route that serves the python state file
      '/api/colonies': {
        bypass: (req, res) => {
          if (req.url === '/api/colonies') {
            try {
              const dataPath = path.resolve(__dirname, '../data/colonies.json')
              if (fs.existsSync(dataPath)) {
                const data = fs.readFileSync(dataPath, 'utf-8')
                res.setHeader('Content-Type', 'application/json')
                res.end(data)
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
