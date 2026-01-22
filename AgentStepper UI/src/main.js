//import 'bootstrap/dist/css/bootstrap.css'

import { createApp } from 'vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import VueDiff from 'vue-diff';
import 'vue-diff/dist/index.css';

/* const lightTheme = {
  dark: false,
  colors: {
    background: '#FFFFFF',
    surface: '#FFFFFF',
    primary: '#6200EE',
    'primary-darken-1': '#3700B3',
    secondary: '#03DAC6',
    'secondary-darken-1': '#018786',
    error: '#B00020',
    info: '#2196F3',
    success: '#4CAF50',
    warning: '#FB8C00',
  },
} */

const vuetify = createVuetify({
    /* theme: {
      defaultTheme: 'lightTheme',
      themes: {
        lightTheme
      }
    }, */
  })

const app = createApp(App);
app.use(vuetify);
app.use(VueDiff);
app.mount('#app');