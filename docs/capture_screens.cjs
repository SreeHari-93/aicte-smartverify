const { chromium } = require('playwright');
const path = require('path');

async function capture() {
  const browser = await chromium.launch({
    channel: 'chrome', // or default bundled chromium
    headless: true
  }).catch(() => chromium.launch({ headless: true }));

  // 1. Desktop (1440 x 900)
  const desktopContext = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const desktopPage = await desktopContext.newPage();
  await desktopPage.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await desktopPage.waitForTimeout(1000);
  const desktopPath = path.join(__dirname, 'desktop_1440.png');
  await desktopPage.screenshot({ path: desktopPath });
  console.log('Saved desktop screenshot:', desktopPath);

  // 2. Mobile (390 x 844)
  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await mobilePage.waitForTimeout(1000);
  const mobilePath = path.join(__dirname, 'mobile_390.png');
  await mobilePage.screenshot({ path: mobilePath });
  console.log('Saved mobile screenshot:', mobilePath);

  await browser.close();
}

capture().catch(err => {
  console.error('Error capturing screenshot:', err);
  process.exit(1);
});

