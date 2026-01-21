/**
 * CanPL.ca API Discovery v2 - Focus on data API calls
 *
 * Specifically targets api-sdp.canpl.ca endpoints
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function discoverSDPAPI() {
    console.log('🔍 Discovering CanPL SDP API endpoints...\n');

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Store discovered API calls
    const apiCalls = [];

    await page.setViewport({ width: 1920, height: 1080 });
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');

    // Intercept requests to the SDP API
    page.on('request', async (request) => {
        const url = request.url();
        if (url.includes('api-sdp.canpl.ca')) {
            console.log(`\n📡 SDP API Request: ${request.method()} ${url}`);
        }
    });

    page.on('response', async (response) => {
        const url = response.url();

        if (url.includes('api-sdp.canpl.ca') || url.includes('widget') && url.includes('api')) {
            console.log(`\n✅ SDP API Response: ${response.status()} ${url}`);

            try {
                const contentType = response.headers()['content-type'] || '';
                if (contentType.includes('json')) {
                    const data = await response.json();
                    apiCalls.push({
                        url: url,
                        method: response.request().method(),
                        status: response.status(),
                        data: data
                    });

                    // Pretty print the response
                    const sample = JSON.stringify(data, null, 2);
                    console.log(`   Data: ${sample.substring(0, 500)}${sample.length > 500 ? '...' : ''}`);
                }
            } catch (e) {
                console.log(`   Could not parse response: ${e.message}`);
            }
        }
    });

    // Navigate to pages that load widgets with data
    const pagesToVisit = [
        { url: 'https://canpl.ca/standings/', name: 'Standings', wait: 5000 },
        { url: 'https://canpl.ca/results/', name: 'Results', wait: 5000 },
        { url: 'https://canpl.ca/schedule/', name: 'Schedule', wait: 5000 },
        { url: 'https://canpl.ca/statistics/', name: 'Statistics', wait: 5000 }
    ];

    for (const pageInfo of pagesToVisit) {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`🔍 Loading ${pageInfo.name}: ${pageInfo.url}`);
        console.log('='.repeat(60));

        try {
            await page.goto(pageInfo.url, {
                waitUntil: 'networkidle0',
                timeout: 30000
            });

            // Wait for widgets to load
            await new Promise(resolve => setTimeout(resolve, pageInfo.wait));

            // Scroll to trigger lazy loading
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await new Promise(resolve => setTimeout(resolve, 2000));

        } catch (e) {
            console.log(`   Error: ${e.message}`);
        }
    }

    // Save results
    const dataDir = path.join(__dirname, '..', 'data');
    const outputPath = path.join(dataDir, 'sdp_api_calls.json');
    fs.writeFileSync(outputPath, JSON.stringify(apiCalls, null, 2));

    console.log(`\n${'='.repeat(60)}`);
    console.log('📋 SUMMARY');
    console.log('='.repeat(60));
    console.log(`Found ${apiCalls.length} SDP API calls`);
    console.log(`Saved to ${outputPath}`);

    if (apiCalls.length > 0) {
        console.log('\n📡 Discovered API Endpoints:');
        apiCalls.forEach((call, i) => {
            console.log(`\n${i + 1}. ${call.method} ${call.url}`);
            if (call.data && typeof call.data === 'object') {
                console.log(`   Keys: ${Object.keys(call.data).join(', ')}`);
            }
        });
    }

    await browser.close();
    return apiCalls;
}

discoverSDPAPI()
    .then(() => {
        console.log('\n🎉 Done!');
        process.exit(0);
    })
    .catch(error => {
        console.error('❌ Error:', error);
        process.exit(1);
    });
