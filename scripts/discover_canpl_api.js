/**
 * CanPL.ca API Discovery Script
 *
 * Uses Puppeteer to monitor network traffic and discover internal API endpoints
 * that canpl.ca uses to load data.
 *
 * Usage: node scripts/discover_canpl_api.js
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function discoverCanPLAPI() {
    console.log('🔍 Discovering CanPL.ca API endpoints...\n');

    const browser = await puppeteer.launch({
        headless: 'new',  // Use new headless mode
        devtools: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Store discovered endpoints
    const apiEndpoints = [];
    const allRequests = [];

    // Set viewport for consistent rendering
    await page.setViewport({ width: 1920, height: 1080 });

    // Set user agent to look like a real browser
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    // Intercept all network requests
    page.on('response', async (response) => {
        const url = response.url();
        const type = response.request().resourceType();
        const status = response.status();
        const method = response.request().method();

        // Log all requests for debugging
        allRequests.push({
            url: url,
            type: type,
            method: method,
            status: status
        });

        // Look for API calls (XHR/Fetch requests)
        if (type === 'xhr' || type === 'fetch') {
            console.log(`\n📡 API Call Detected:`);
            console.log(`   URL: ${url}`);
            console.log(`   Method: ${method}`);
            console.log(`   Status: ${status}`);
            console.log(`   Type: ${type}`);

            // Try to get JSON response
            try {
                const contentType = response.headers()['content-type'] || '';

                if (contentType.includes('application/json') || contentType.includes('text/json')) {
                    const text = await response.text();
                    let data;
                    try {
                        data = JSON.parse(text);
                    } catch (e) {
                        data = text;
                    }

                    console.log(`   ✅ JSON Response!`);
                    const sampleStr = JSON.stringify(data, null, 2);
                    console.log(`   Sample: ${sampleStr.substring(0, 300)}${sampleStr.length > 300 ? '...' : ''}`);

                    // Save endpoint details
                    apiEndpoints.push({
                        url: url,
                        method: method,
                        status: status,
                        contentType: contentType,
                        sampleData: sampleStr.substring(0, 2000),
                        dataKeys: typeof data === 'object' ? Object.keys(data) : [],
                        isArray: Array.isArray(data),
                        itemCount: Array.isArray(data) ? data.length : (typeof data === 'object' ? Object.keys(data).length : 0)
                    });
                }
            } catch (e) {
                // Not JSON or couldn't read, skip
                console.log(`   ⚠️ Could not read response: ${e.message}`);
            }
        }

        // Also look for interesting URLs that might be API endpoints
        if (url.includes('/api/') || url.includes('/v1/') || url.includes('/graphql') ||
            url.includes('.json') || url.includes('ajax') || url.includes('data')) {
            if (!apiEndpoints.find(e => e.url === url)) {
                console.log(`\n🔗 Potential API URL found: ${url}`);
            }
        }
    });

    // Navigate to various CPL pages to discover endpoints
    const pagesToVisit = [
        { url: 'https://canpl.ca/', name: 'Home' },
        { url: 'https://canpl.ca/results/', name: 'Results' },
        { url: 'https://canpl.ca/standings/', name: 'Standings' },
        { url: 'https://canpl.ca/statistics/', name: 'Statistics' },
        { url: 'https://canpl.ca/schedule/', name: 'Schedule' },
        { url: 'https://canpl.ca/clubs/', name: 'Clubs' }
    ];

    for (const pageInfo of pagesToVisit) {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`🔍 Navigating to ${pageInfo.name}: ${pageInfo.url}`);
        console.log('='.repeat(60));

        try {
            await page.goto(pageInfo.url, {
                waitUntil: 'networkidle2',
                timeout: 30000
            });

            // Wait for dynamic content to load
            await new Promise(resolve => setTimeout(resolve, 3000));

            // Scroll down to trigger lazy loading
            await page.evaluate(() => {
                window.scrollTo(0, document.body.scrollHeight / 2);
            });
            await new Promise(resolve => setTimeout(resolve, 2000));

            await page.evaluate(() => {
                window.scrollTo(0, document.body.scrollHeight);
            });
            await new Promise(resolve => setTimeout(resolve, 2000));

        } catch (e) {
            console.log(`   ❌ Error loading ${pageInfo.name}: ${e.message}`);
        }
    }

    // Try to interact with dropdowns/filters that might trigger API calls
    console.log(`\n${'='.repeat(60)}`);
    console.log('🔍 Looking for interactive elements...');
    console.log('='.repeat(60));

    try {
        // Go back to results page and try to interact
        await page.goto('https://canpl.ca/results/', { waitUntil: 'networkidle2' });
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Look for season/year selectors
        const selectors = ['select', '[role="combobox"]', '.dropdown', '.filter'];
        for (const selector of selectors) {
            const elements = await page.$$(selector);
            console.log(`   Found ${elements.length} elements matching '${selector}'`);
        }

    } catch (e) {
        console.log(`   ⚠️ Error interacting: ${e.message}`);
    }

    // Save discovered endpoints
    const dataDir = path.join(__dirname, '..', 'data');
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }

    const report = {
        discoveredAt: new Date().toISOString(),
        totalEndpoints: apiEndpoints.length,
        totalRequests: allRequests.length,
        endpoints: apiEndpoints,
        summary: {
            jsonEndpoints: apiEndpoints.filter(e => e.contentType?.includes('json')).length,
            uniqueDomains: [...new Set(apiEndpoints.map(e => new URL(e.url).hostname))]
        }
    };

    const outputPath = path.join(dataDir, 'discovered_canpl_endpoints.json');
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));

    // Also save all requests for analysis
    const allRequestsPath = path.join(dataDir, 'all_canpl_requests.json');
    fs.writeFileSync(allRequestsPath, JSON.stringify(allRequests, null, 2));

    console.log(`\n${'='.repeat(60)}`);
    console.log('✅ Discovery complete!');
    console.log('='.repeat(60));
    console.log(`📝 Found ${apiEndpoints.length} API endpoints`);
    console.log(`📊 Total requests observed: ${allRequests.length}`);
    console.log(`💾 Saved to ${outputPath}`);
    console.log(`📋 All requests saved to ${allRequestsPath}`);

    if (apiEndpoints.length > 0) {
        console.log('\n📡 Discovered Endpoints:');
        apiEndpoints.forEach((ep, i) => {
            console.log(`\n   ${i + 1}. ${ep.method} ${ep.url}`);
            console.log(`      Status: ${ep.status}`);
            console.log(`      Keys: ${ep.dataKeys.join(', ') || 'N/A'}`);
        });
    } else {
        console.log('\n⚠️ No JSON API endpoints discovered.');
        console.log('   The site may use server-side rendering or a different data approach.');
        console.log('   Falling back to FBref scraping (TASK 1.2) is recommended.');
    }

    await browser.close();

    return report;
}

// Run if called directly
if (require.main === module) {
    discoverCanPLAPI()
        .then(report => {
            console.log('\n🎉 Done!');
            process.exit(0);
        })
        .catch(error => {
            console.error('❌ Error:', error);
            process.exit(1);
        });
}

module.exports = { discoverCanPLAPI };
