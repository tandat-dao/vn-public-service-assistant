import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    screens: {
      sm: '768px',
      md: '992px',
      lg: '1200px',
    },
    extend: {
      colors: {
        primary: {
          DEFAULT: '#CE7A58',
          dark:    '#903938',
          hover:   '#B8694A',
          light:   '#F5E8DF',
        },
        cta: { DEFAULT: '#FFC251', text: '#000000' },
        nav: { bg: '#F5F5F5' },
        brand: {
          text:   '#1E2F41',
          sub:    '#555555',
          border: '#DDDDDD',
          link:   '#2A6EBB',
        },
        icon: {
          congdan:     '#3D9E8D',
          doanhnghiep: '#CE7A58',
          hoso:        '#4A7AA8',
        },
        score:  { DEFAULT: '#28A745' },
        footer: { DEFAULT: '#903938' },
      },
      fontFamily: {
        sans: ['Nunito', 'Arial', 'sans-serif'],
      },
      maxWidth: {
        container: '1170px',
      },
      borderRadius: {
        DEFAULT: '4px',
        sm:   '3px',
        md:   '4px',
        lg:   '6px',
        xl:   '6px',
        '2xl':'6px',
        full: '9999px',
      },
    },
  },
  plugins: [],
}

export default config
