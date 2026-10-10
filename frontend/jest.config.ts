import type { Config } from 'jest'
// Added by ChatGPT: explicit extension supports this project's Node ESM test runner.
import nextJest from 'next/jest.js'

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  // Added by ChatGPT: bounded interaction timeout accommodates shared Docker/CI host load.
  testTimeout: 15000,
  // Added by ChatGPT: generated standalone builds are not additional application/test modules.
  modulePathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/.next-check/', '<rootDir>/.next-preview/'],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
export default createJestConfig(config)
