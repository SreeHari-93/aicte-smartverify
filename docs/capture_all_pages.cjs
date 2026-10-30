const { chromium } = require('../frontend/node_modules/playwright');
const path = require('path');
const http = require('http');

const pages = [
  { name: '1_dashboard', path: '/institute/dashboard' },
  { name: '2_certificates', path: '/institute/certificates' },
  { name: '3_applications', path: '/institute/applications' },
  { name: '4_rules', path: '/institute/rules' },
  { name: '5_upload', path: '/institute/upload' },
  { name: '6_validation', path: '/institute/validation' },
  { name: '7_complaints', path: '/institute/complaints' },
  { name: '8_reports', path: '/institute/reports' },
];

async function captureAll() {
  const browser = await chromium.launch({ channel: 'chrome' }).catch(() => chromium.launch());

  // 1. Desktop context (1440 x 900)
  const dContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const dPage = await dContext.newPage();

  // Login
  await dPage.goto('http://localhost:5173/login');
  await dPage.waitForTimeout(500);

  // Get captcha directly via evaluate to ensure valid captcha
  const captchaId = await dPage.evaluate(() => {
    const img = document.querySelector('img[alt="Security Captcha Challenge"]');
    return img ? true : false;
  });

  // Perform quick backend login to set cookies directly in context
  const cookies = await dPage.evaluate(async () => {
    // 1. Get captcha
    const cRes = await fetch('/api/auth/captcha');
    const cData = await cRes.json();
    // 2. We can login directly via fetch
    const lRes = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role: 'INSTITUTE',
        institute_id: 'SKCET01',
        password: 'Institute@123',
        captcha_id: cData.captcha_id,
        captcha_text: 'DUMMY', // wait, need actual text or seed captcha
      })
    });
    return lRes.status;
  });

  // Let's create a known token directly for playwright context using python or script
  console.log('Browser launched. Injecting session...');
  await browser.close();
}

captureAll().catch(console.error);

