const { chromium } = require('../frontend/node_modules/playwright');
const fs = require('fs');
const { execSync } = require('child_process');

// Generate access token for SKCET user id=1
const token = execSync('backend\\venv\\Scripts\\python -c "from backend.app.security.tokens import create_access_token; print(create_access_token(6, \'INSTITUTE\'))"').toString().trim();

(async () => {
  const browser = await chromium.launch({ headless: true });

  const viewports = [
    { name: 'cert_1280', width: 1280, height: 900, url: 'http://localhost:5173/institute/certificates' },
    { name: 'cert_1366', width: 1366, height: 900, url: 'http://localhost:5173/institute/certificates' },
    { name: 'cert_1440', width: 1440, height: 900, url: 'http://localhost:5173/institute/certificates' },
    { name: 'cert_1920', width: 1920, height: 1080, url: 'http://localhost:5173/institute/certificates' },
    { name: 'cert_390', width: 390, height: 844, url: 'http://localhost:5173/institute/certificates', isMobile: true },
    { name: 'rules_1440', width: 1440, height: 1000, url: 'http://localhost:5173/institute/rules' },
    { name: 'rules_deeplink', width: 1440, height: 1000, url: 'http://localhost:5173/institute/rules?rule=APH-2026-CH2-R02' },
    { name: 'rules_390', width: 390, height: 844, url: 'http://localhost:5173/institute/rules', isMobile: true },
  ];

  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: !!vp.isMobile
    });
    await context.addCookies([{
      name: 'aicte_access_token',
      value: token,
      domain: 'localhost',
      path: '/'
    }]);
    const page = await context.newPage();
    await page.goto(vp.url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Check if table or card container has horizontal scrollbar
    if (vp.name.startsWith('cert_') && !vp.isMobile) {
      const scrollInfo = await page.evaluate(() => {
        const table = document.querySelector('table');
        const card = table ? table.closest('.rounded-\\[12px\\]') : null;
        return {
          tableScrollWidth: table ? table.scrollWidth : 0,
          tableClientWidth: table ? table.clientWidth : 0,
          cardScrollWidth: card ? card.scrollWidth : 0,
          cardClientWidth: card ? card.clientWidth : 0,
        };
      });
      console.log(`[${vp.name}] Table client: ${scrollInfo.tableClientWidth}, scroll: ${scrollInfo.tableScrollWidth}. Card client: ${scrollInfo.cardClientWidth}, scroll: ${scrollInfo.cardScrollWidth}`);
    }

    const outPath = `d:/aicte/docs/${vp.name}.png`;
    await page.screenshot({ path: outPath, fullPage: false });
    await context.close();
  }

  await browser.close();
  console.log('All verification screenshots captured successfully!');
})();
