const path = require('path');
const { chromium } = require(path.join(__dirname, '../frontend/node_modules/playwright'));
const { execSync } = require('child_process');

// Generate fresh token via python
const token = execSync('backend\\venv\\Scripts\\python -c "from backend.app.database import SessionLocal; from backend.app.models.user import User; from backend.app.security.tokens import create_access_token; db=SessionLocal(); u=db.query(User).filter(User.email==\'skcet@aicte.edu.in\').first(); print(create_access_token(u.id, u.role))"')
  .toString()
  .trim();

console.log('Obtained fresh token:', token.substring(0, 20) + '...');

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

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' }).catch(() => chromium.launch());

  // 1. Desktop 1440px
  console.log('Capturing Desktop 1440px views...');
  const dContext = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  await dContext.addCookies([
    {
      name: 'aicte_access_token',
      value: token,
      domain: 'localhost',
      path: '/'
    }
  ]);
  const dPage = await dContext.newPage();

  for (const p of pages) {
    await dPage.goto(`http://localhost:5173${p.path}`, { waitUntil: 'networkidle' });
    await dPage.waitForTimeout(600);
    const ssPath = path.join(__dirname, `page_screenshots/desktop_${p.name}.png`);
    await dPage.screenshot({ path: ssPath, fullPage: false });
    console.log(`  + Saved desktop_${p.name}.png`);
  }

  // 2. Mobile 390px
  console.log('Capturing Mobile 390px views...');
  const mContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true
  });
  await mContext.addCookies([
    {
      name: 'aicte_access_token',
      value: token,
      domain: 'localhost',
      path: '/'
    }
  ]);
  const mPage = await mContext.newPage();

  for (const p of pages) {
    await mPage.goto(`http://localhost:5173${p.path}`, { waitUntil: 'networkidle' });
    await mPage.waitForTimeout(600);
    const ssPath = path.join(__dirname, `page_screenshots/mobile_${p.name}.png`);
    await mPage.screenshot({ path: ssPath, fullPage: false });
    console.log(`  + Saved mobile_${p.name}.png`);
  }

  await browser.close();
  console.log('All 16 screenshots captured successfully!');
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
