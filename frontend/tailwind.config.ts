import type { Config } from 'tailwindcss'

export default {
    content: [
        './components/**/*.{vue,js,ts}',
        './layouts/**/*.vue',
        './pages/**/*.vue',
        './app/**/*.{vue,js,ts}',
        './plugins/**/*.{js,ts}',
        './nuxt.config.{js,ts}',
    ],
    theme: {
        extend: {
            colors: {
                // High-contrast industrial surface colors
                surface: {
                    DEFAULT: '#0f0f13',
                    elevated: '#1a1a24',
                    muted: '#222222',
                },
                edge: {
                    DEFAULT: '#333333',
                    dark: '#222222',
                    light: '#444444',
                }
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', 'monospace'],
                sans: ['Inter', 'system-ui', 'sans-serif'], // For the few non-data labels
            }
        },
    },
    plugins: [],
} satisfies Config
