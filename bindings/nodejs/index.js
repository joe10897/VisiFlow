const fetch = require('node-fetch');

class VisiPage {
    /**
     * Wrap a Playwright Node.js Page object with VisiFlow visual actions.
     * @param {import('playwright').Page} page - Playwright Page instance
     * @param {Object} options - Configuration options
     * @param {string} [options.daemonUrl='http://127.0.0.1:8000'] - Local VisiFlow daemon URL
     */
    constructor(page, options = {}) {
        this.page = page;
        this.daemonUrl = options.daemonUrl || 'http://127.0.0.1:8000';
    }

    async _resolveCoordinates(textOrLabel) {
        const screenshotBuffer = await this.page.screenshot();
        const base64Image = screenshotBuffer.toString('base64');

        const params = new URLSearchParams();
        params.append('image_base64', base64Image);
        params.append('query', textOrLabel);

        try {
            const response = await fetch(`${this.daemonUrl}/match`, {
                method: 'POST',
                body: params
            });

            if (!response.ok) {
                console.warn(`[VisiFlow-JS] Daemon HTTP status ${response.status}`);
                return null;
            }

            const data = await response.json();
            if (data && data.found) {
                return { x: data.x, y: data.y };
            }
            return null;
        } catch (err) {
            console.error(`[VisiFlow-JS] Could not connect to daemon at ${this.daemonUrl}. Make sure 'visiflow server' is running.`, err.message);
            return null;
        }
    }

    async visualClick(textOrLabel, timeoutMs = 10000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            const coords = await this._resolveCoordinates(textOrLabel);
            if (coords) {
                await this.page.mouse.click(coords.x, coords.y);
                console.log(`[VisiFlow-JS] Visual Click on '${textOrLabel}' at (${coords.x}, ${coords.y})`);
                return true;
            }
            await new Promise(r => setTimeout(r, 500));
        }
        throw new Error(`[VisiFlow-JS] Could not visually locate element '${textOrLabel}' within ${timeoutMs}ms`);
    }

    async visualPress(key, timeoutMs = 10000) {
        const cleanKey = key.replace(/[{}]/g, "");
        const titleKey = cleanKey.charAt(0).toUpperCase() + cleanKey.slice(1);
        await this.page.keyboard.press(titleKey);
        console.log(`[VisiFlow-JS] Visual Press keyboard key: ${titleKey}`);
        return true;
    }

    async visualFill(textOrLabel, value, timeoutMs = 10000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            const coords = await this._resolveCoordinates(textOrLabel);
            if (coords) {
                await this.page.mouse.click(coords.x, coords.y, { clickCount: 3 });
                await this.page.keyboard.press('Backspace');
                await this.page.keyboard.type(value);
                console.log(`[VisiFlow-JS] Visual Fill on '${textOrLabel}' with '${value}'`);
                return true;
            }
            await new Promise(r => setTimeout(r, 500));
        }
        throw new Error(`[VisiFlow-JS] Could not visually locate input field '${textOrLabel}' within ${timeoutMs}ms`);
    }

    async visualWaitFor(textOrLabel, timeoutMs = 10000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            const coords = await this._resolveCoordinates(textOrLabel);
            if (coords) {
                console.log(`[VisiFlow-JS] Visual element '${textOrLabel}' is present.`);
                return true;
            }
            await new Promise(r => setTimeout(r, 500));
        }
        throw new Error(`[VisiFlow-JS] Timed out waiting for visual element '${textOrLabel}'`);
    }

    async visualAssertVisible(textOrLabel, timeoutMs = 10000) {
        try {
            await this.visualWaitFor(textOrLabel, timeoutMs);
            console.log(`[VisiFlow-JS] Assertion PASSED: Element '${textOrLabel}' is visible.`);
            return true;
        } catch (err) {
            throw new Error(`[VisiFlow-JS] Assertion FAILED: Element '${textOrLabel}' is not visible. Error: ${err.message}`);
        }
    }

    async visualAssertNotVisible(textOrLabel, timeoutMs = 5000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            const coords = await this._resolveCoordinates(textOrLabel);
            if (!coords) {
                console.log(`[VisiFlow-JS] Assertion PASSED: Element '${textOrLabel}' is not visible.`);
                return true;
            }
            await new Promise(r => setTimeout(r, 500));
        }
        throw new Error(`[VisiFlow-JS] Assertion FAILED: Element '${textOrLabel}' is still visible after ${timeoutMs}ms`);
    }
}

module.exports = { VisiPage };
