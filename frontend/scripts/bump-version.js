import { readFileSync, writeFileSync } from 'fs'

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'))
const parts = pkg.version.split('.').map(Number)

// Incrementa el patch (0.0.X)
parts[2] += 1

pkg.version = parts.join('.')
writeFileSync('./package.json', JSON.stringify(pkg, null, 2))
console.log(`Version actualizada a ${pkg.version}`)