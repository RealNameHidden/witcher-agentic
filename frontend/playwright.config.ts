import {defineConfig} from '@playwright/test';
const deployedURL=process.env.PLAYWRIGHT_BASE_URL;
export default defineConfig({
  testDir:'./e2e',workers:1,timeout:40000,
  use:{baseURL:deployedURL||'http://127.0.0.1:4173',headless:true},
  webServer:deployedURL?undefined:{command:'npm run preview -- --port 4173',url:'http://127.0.0.1:4173',reuseExistingServer:false},
});
