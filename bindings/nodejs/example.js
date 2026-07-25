const path = require('path');
const { chromium } = require('playwright');
const { VisiPage } = require('./index');

(async () => {
    console.log('🚀 Starting VisiFlow Node.js Playwright Integration Example...');

    const testPagePath = path.resolve(__dirname, '../../tests/index.html');
    const testPageUrl = `file:///${testPagePath.replace(/\\/g, '/')}`;

    const browser = await chromium.launch({ headless: true });
    const context = await browser.new_context({ viewport: { width: 1280, height: 720 } });
    const page = await context.new_page();

    console.log(`Navigating to: ${testPageUrl}`);
    await page.goto(testPageUrl);

    // Wrap standard Playwright Page
    const visipage = new VisiPage(page, { daemonUrl: 'http://127.0.0.1:8000' });

    try {
        console.log('Filling Username visually...');
        await visipage.visualFill('Username', 'nodejs_dev');

        console.log('Filling Password visually...');
        await visipage.visualFill('Password', 'node_secret_999');

        console.log('Clicking Submit button visually...');
        await visipage.visualClick('Submit');

        console.log('Waiting for login success alert...');
        await visipage.visualWaitFor('Logged in successfully!');

        console.log('✅ Node.js VisiFlow Playwright automation test PASSED!');
    } catch (err) {
        console.error('❌ Node.js VisiFlow test failed:', err);
    } finally {
        await browser.close();
    }
})();
