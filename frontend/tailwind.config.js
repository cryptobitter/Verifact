/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./*.html",
    "./js/**/*.js",
    "./src_old/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#FFFFFF',
        'bg-soft': '#FFF4E8',
        surface: '#FFFFFF',
        'surface-alt': '#FAF6F1',
        border: '#EADFD3',
        text: '#1F1612',
        'text-muted': '#6B5B52',
        primary: {
          DEFAULT: '#C8512D',
          hover: '#B04624',
          contrast: '#FFFFFF',
          container: '#FBE3D6'
        },
        accent: {
          DEFAULT: '#F5A524',
          text: '#1F1612'
        },
        blush: '#FBE3D6',
        deep: '#3A1F14',
        status: {
          urgent: '#D92D20',
          review: '#F5A524',
          routine: '#3A1F14',
          discordant: '#E5799A',
          signed: '#C8512D'
        },
        // Stitch Material Compatibility mapping to Terracotta & Saffron
        'surface-container-lowest': '#FFFFFF',
        'surface-container-low': '#FFF4E8',
        'surface-container': '#FAF6F1',
        'surface-container-high': '#F5ECE1',
        'surface-container-highest': '#EADFD3',
        'on-surface': '#1F1612',
        'on-surface-variant': '#6B5B52',
        'outline': '#C5B4A5',
        'outline-variant': '#EADFD3',
        'primary-container': '#FBE3D6',
        'on-primary': '#FFFFFF',
        'on-primary-container': '#1F1612',
        'secondary': '#3A1F14',
        'secondary-container': '#FAF6F1',
        'on-secondary-container': '#1F1612',
        'tertiary': '#F5A524',
        'tertiary-container': '#FFF4E8',
        'on-tertiary-container': '#1F1612',
        'tertiary-fixed': '#F5A524',
        'on-tertiary-fixed': '#1F1612',
        'error': '#D92D20',
        'error-container': '#FDE8E8',
        'on-error-container': '#D92D20',
        'inverse-surface': '#3A1F14',
        'inverse-on-surface': '#FAF6F1'
      }
    }
  },
  plugins: [],
}
