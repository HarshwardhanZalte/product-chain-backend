import { spawnSync } from 'node:child_process'
import { readdirSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'

function collectSourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) return collectSourceFiles(path)
    return /\.(?:js|jsx|ts|tsx)$/.test(entry.name)
      ? [relative(process.cwd(), path).split(sep).join('/')]
      : []
  })
}

const files = collectSourceFiles(resolve('src'))
const result = spawnSync(
  process.execPath,
  [resolve('node_modules/oxlint/bin/oxlint'), '--react-plugin', ...files],
  { stdio: 'inherit' },
)

if (result.error) {
  console.error(result.error)
  process.exit(1)
}
process.exit(result.status ?? 1)
