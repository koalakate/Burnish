import { test, expect, type Page, type Route } from "@playwright/test";

// ---------------------------------------------------------------------------
// Mock data — realistic responses matching the API contract
// ---------------------------------------------------------------------------

const DECK_ID = "deck-001";
const CHECK_RUN_ID = "chk-001";

const CORRECTIONS = [
  {
    id: "cor-1",
    rule_type: "color",
    severity: "error" as const,
    message: "Off-brand fill color on title shape",
    element_id: "el-title",
    original_value: "#FF0000",
    expected_value: "#1A73E8",
    correction_status: "pending" as const,
  },
  {
    id: "cor-2",
    rule_type: "font",
    severity: "warning" as const,
    message: "Font changed: Comic Sans → Inter",
    element_id: "el-body",
    original_value: "Comic Sans MS",
    expected_value: "Inter",
    correction_status: "pending" as const,
  },
  {
    id: "cor-3",
    rule_type: "contrast",
    severity: "warning" as const,
    message: "Low contrast on subtitle text",
    element_id: "el-sub",
    original_value: "#CCCCCC",
    expected_value: "#333333",
    correction_status: "pending" as const,
  },
];

// Keep mutable state so mutations can update it
function freshCorrections() {
  return CORRECTIONS.map((c) => ({ ...c, correction_status: "pending" as const }));
}

// 1×1 transparent PNG as a data URI for thumbnail mocking
const TINY_PNG =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

// ---------------------------------------------------------------------------
// Helper — set up API route mocks for the full flow
// ---------------------------------------------------------------------------

async function mockApiRoutes(page: Page) {
  const corrections = freshCorrections();
  let fixAllApplied = false;

  const API = "http://localhost:8000";

  // Upload deck
  await page.route(`${API}/api/decks/upload`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ deck_id: DECK_ID }),
    });
  });

  // Trigger check
  await page.route(`${API}/api/decks/${DECK_ID}/check`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ check_run_id: CHECK_RUN_ID }),
    });
  });

  // Check run status — first call returns "running", subsequent return "complete"
  let checkPollCount = 0;
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}`, async (route: Route) => {
    if (route.request().url().includes("/slides/") || route.request().url().includes("/corrections") || route.request().url().includes("/fix-all") || route.request().url().includes("/export")) {
      return route.fallback();
    }
    checkPollCount++;
    const isComplete = checkPollCount > 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: CHECK_RUN_ID,
        deck_id: DECK_ID,
        status: isComplete ? "complete" : "running",
        dqs_overall: isComplete ? 62 : null,
        issue_count_error: isComplete ? 1 : 0,
        issue_count_warning: isComplete ? 2 : 0,
        issue_count_info: 0,
        created_at: "2026-04-01T10:00:00Z",
        started_at: "2026-04-01T10:00:01Z",
        completed_at: isComplete ? "2026-04-01T10:00:05Z" : null,
        slides: isComplete
          ? [
              {
                slide_index: 0,
                dqs_slide: 62,
                thumbnail_url: TINY_PNG,
              },
            ]
          : [],
      }),
    });
  });

  // Corrections list
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}/corrections`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        check_run_id: CHECK_RUN_ID,
        slides: [
          {
            slide_index: 0,
            corrections: corrections.map((c) => ({ ...c })),
          },
        ],
        total: corrections.length,
      }),
    });
  });

  // Accept a correction
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}/corrections/*/accept`, async (route: Route) => {
    const url = route.request().url();
    const match = url.match(/corrections\/([^/]+)\/accept/);
    const id = match?.[1];
    const c = corrections.find((x) => x.id === id);
    if (c) c.correction_status = "accepted" as never;
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  // Dismiss a correction
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}/corrections/*/dismiss`, async (route: Route) => {
    const url = route.request().url();
    const match = url.match(/corrections\/([^/]+)\/dismiss/);
    const id = match?.[1];
    const c = corrections.find((x) => x.id === id);
    if (c) c.correction_status = "rejected" as never;
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  // Fix all
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}/fix-all`, async (route: Route) => {
    for (const c of corrections) {
      if (c.correction_status === "pending") c.correction_status = "accepted" as never;
    }
    fixAllApplied = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  // Export download
  await page.route(`${API}/api/checks/${CHECK_RUN_ID}/export`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        check_run_id: CHECK_RUN_ID,
        download_url: `${API}/files/corrected-deck.pptx`,
        dqs_after: 91,
      }),
    });
  });

  // Mock the actual file download so it doesn't 404
  await page.route(`${API}/files/corrected-deck.pptx`, async (route: Route) => {
    // Minimal valid-ish binary response
    await route.fulfill({
      status: 200,
      contentType: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      body: Buffer.from("PK-mock-pptx-content"),
    });
  });

  return { corrections, isFixAllApplied: () => fixAllApplied };
}

// ---------------------------------------------------------------------------
// Clerk auth bypass — mock the session so protected pages render
// ---------------------------------------------------------------------------

async function bypassClerkAuth(page: Page) {
  // Intercept Clerk's client-side session check to avoid redirect to sign-in
  await page.route("**/v1/client*", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        response: {
          id: "sess_test",
          status: "active",
          last_active_organization_id: "org_test",
          user: { id: "user_test", first_name: "Jake", last_name: "Test" },
        },
        client: {
          id: "client_test",
          sessions: [
            {
              id: "sess_test",
              status: "active",
              user: { id: "user_test", first_name: "Jake" },
            },
          ],
          sign_in: null,
          sign_up: null,
        },
      }),
    });
  });
}

// ---------------------------------------------------------------------------
// Test: Jake's journey — Upload → Check → Fix All → Download
// ---------------------------------------------------------------------------

test.describe("Upload-Check-Fix E2E", () => {
  test("Jake: upload PPTX → check results → Fix All → download corrected PPTX", async ({
    page,
  }) => {
    const startTime = Date.now();

    await bypassClerkAuth(page);
    await mockApiRoutes(page);

    // 1. Navigate to upload page
    await page.goto("/decks/upload");

    // Verify the upload page renders
    await expect(page.getByText("Upload")).toBeVisible();
    await expect(
      page.getByText("Drop a .pptx file to check it against your brand rules")
    ).toBeVisible();

    // 2. Upload a file via the dropzone
    //    Playwright can set input files even on hidden inputs
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "brand_violations.pptx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      buffer: Buffer.from("PK-test-pptx-content"),
    });

    // 3. Should navigate to deck detail page after upload
    await page.waitForURL(/\/decks\//, { timeout: 15_000 });

    // 4. Navigate to check results (simulating user triggering check after ingestion)
    await page.goto(`/checks/${CHECK_RUN_ID}`);
    await expect(page.getByText("Check Results")).toBeVisible();

    // 5. Check results page should show polling first, then complete
    await expect(page.getByText("Check complete")).toBeVisible({
      timeout: 10_000,
    });

    // 6. Verify issues are displayed
    await expect(page.getByText("1")).toBeVisible(); // error count
    await expect(page.getByText("error")).toBeVisible();

    // 7. Verify DQS badge is shown
    await expect(page.getByText("62")).toBeVisible();

    // 8. Click "View corrections" link
    await page.getByText("View corrections →").click();
    await page.waitForURL(/\/corrections/, { timeout: 10_000 });

    // 8. Corrections page should show the corrections
    await expect(page.getByText("Corrections")).toBeVisible();
    await expect(page.getByText("3 total")).toBeVisible();

    // 9. Verify individual correction messages
    await expect(
      page.getByText("Off-brand fill color on title shape")
    ).toBeVisible();
    await expect(page.getByText("Font changed: Comic Sans → Inter")).toBeVisible();

    // 10. Click "Fix All" button
    const fixAllButton = page.getByRole("button", { name: /Fix All/ });
    await expect(fixAllButton).toBeVisible();
    await fixAllButton.click();

    // 11. After Fix All, download button should appear
    await expect(
      page.getByRole("button", { name: /Download PPTX/ })
    ).toBeVisible({ timeout: 10_000 });

    // 12. Verify the DQS confirmation badge shows improved score
    await expect(page.getByText("Corrections applied")).toBeVisible();
    await expect(page.getByText("91")).toBeVisible();

    // 13. Click download — verify a download is triggered
    const downloadPromise = page.waitForEvent("download", { timeout: 10_000 });
    // Click the first Download PPTX button (there may be two — in confirmation box and header)
    await page.getByRole("button", { name: /Download PPTX/ }).first().click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("corrected-deck.pptx");

    // 14. Jake's mandate: entire flow in under 2 minutes
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(120_000);
  });

  // ---------------------------------------------------------------------------
  // Test: Priya's journey — Dismiss one, accept the rest, download
  // ---------------------------------------------------------------------------

  test("Priya: dismiss one correction, accept the rest, then download", async ({
    page,
  }) => {
    await bypassClerkAuth(page);
    const { corrections } = await mockApiRoutes(page);

    // Navigate directly to corrections page
    await page.goto(`/checks/${CHECK_RUN_ID}/corrections`);

    // Wait for corrections to load
    await expect(page.getByText("3 total")).toBeVisible({ timeout: 10_000 });

    // 1. Dismiss the first correction (color issue)
    const firstCard = page.getByText("Off-brand fill color on title shape");
    await firstCard.click();
    // Find the Dismiss button near the first correction
    const dismissButton = page
      .getByText("Off-brand fill color on title shape")
      .locator("../..")
      .getByRole("button", { name: /Dismiss/ });
    await dismissButton.click();

    // 2. Accept the second correction (font issue)
    const secondCard = page.getByText("Font changed: Comic Sans → Inter");
    await secondCard.click();
    const acceptButton2 = page
      .getByText("Font changed: Comic Sans → Inter")
      .locator("../..")
      .getByRole("button", { name: /Accept/ });
    await acceptButton2.click();

    // 3. Use edit-in-place on the third correction (contrast issue)
    const thirdCard = page.getByText("Low contrast on subtitle text");
    await thirdCard.click();
    const editButton = page
      .getByText("Low contrast on subtitle text")
      .locator("../..")
      .getByRole("button", { name: /Edit/ });
    await editButton.click();

    // Modify the value in the inline editor
    const editInput = page.locator('input[type="text"]');
    await editInput.clear();
    await editInput.fill("#222222");

    // Save the edit (click the check/save button in the editor)
    const saveButton = page.locator(
      '.mt-2.flex.gap-1\\.5 button[class*="default"]'
    );
    await saveButton.click();

    // 4. After all resolved, the "Fix All" button should disappear and download appears
    //    (The mock refetches corrections — all now resolved)
    await expect(
      page.getByRole("button", { name: /Download PPTX/ })
    ).toBeVisible({ timeout: 10_000 });

    // 5. Download the corrected PPTX
    const downloadPromise = page.waitForEvent("download", { timeout: 10_000 });
    await page.getByRole("button", { name: /Download PPTX/ }).first().click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("corrected-deck.pptx");
  });

  // ---------------------------------------------------------------------------
  // Test: Timing assertion — wall-clock time under 2 minutes
  // ---------------------------------------------------------------------------

  test("flow completes within 2 minutes wall-clock time", async ({ page }) => {
    const start = Date.now();

    await bypassClerkAuth(page);
    await mockApiRoutes(page);

    // Run the full flow
    await page.goto("/decks/upload");
    await page.locator('input[type="file"]').setInputFiles({
      name: "timing_test.pptx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      buffer: Buffer.from("PK-timing-test"),
    });

    await page.waitForURL(/\/decks\//, { timeout: 15_000 });

    // Navigate to check results (simulating check trigger after ingestion)
    await page.goto(`/checks/${CHECK_RUN_ID}`);
    await expect(page.getByText("Check complete")).toBeVisible({
      timeout: 10_000,
    });
    await page.getByText("View corrections →").click();
    await page.waitForURL(/\/corrections/, { timeout: 10_000 });

    const fixAllButton = page.getByRole("button", { name: /Fix All/ });
    await expect(fixAllButton).toBeVisible({ timeout: 10_000 });
    await fixAllButton.click();

    await expect(
      page.getByRole("button", { name: /Download PPTX/ })
    ).toBeVisible({ timeout: 10_000 });

    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(120_000); // Jake's 2-minute mandate
  });
});
