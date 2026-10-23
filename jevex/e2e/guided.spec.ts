import { expect, test } from "@playwright/test";
import { GUIDED } from "../src/web/guided.ts";

const ANSWERING_VIEWS = new Set(["intent", "flags", "triage", "extract", "scan"]);

test.beforeEach(async ({ context }) => {
  // Network blocked: only the app's own static files load. No /api, nothing external.
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    const local = url.hostname === "localhost" || url.hostname === "127.0.0.1";
    return local && !url.pathname.includes("/api/") ? route.continue() : route.abort();
  });
});

test("the guided script runs end to end from recordings with the network blocked", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/#/guided/1");
  await expect(page.getByTestId("mode-pill")).toContainText("live unavailable");

  for (const [i, step] of GUIDED.entries()) {
    await expect(page.getByTestId("guided-step")).toHaveText(`${i + 1} / ${GUIDED.length}`);
    await expect(page.locator(".guided-title")).toHaveText(step.title);

    if (ANSWERING_VIEWS.has(step.view) && step.start?.kind !== "blank") {
      await expect(page.getByTestId("jev-answer")).toHaveAttribute("data-source", "recorded");
    }
    if (step.view === "scoreboard") await expect(page.getByTestId("score-intent")).toContainText("%");
    if (step.view === "keep") await expect(page.getByTestId("keep-table")).toBeVisible();
    if (step.start?.kind === "blank") await expect(page.getByTestId("email-input")).toHaveValue("");
    await expect(page.getByTestId("not-recorded")).toHaveCount(0);
    await expect(page.getByTestId("jev-error")).toHaveCount(0);

    if (i === 0) {
      await page.keyboard.press("n");
      await expect(page.getByTestId("speaker-note-text")).toHaveText(step.note);
      await page.keyboard.press("n");
    }
    await page.keyboard.press("ArrowRight");
  }
  expect(errors).toEqual([]);
});

test("free play and guided mode show the same station screen", async ({ page }) => {
  await page.goto("/#/flags");
  await page.getByRole("button", { name: "Third time writing" }).click();
  const free = await page.locator(".col-jev .jev-flags").innerText();
  await page.goto("/#/guided/3");
  await expect(page.locator(".col-jev .jev-flags")).toBeVisible();
  expect(await page.locator(".col-jev .jev-flags").innerText()).toBe(free);
});

test("L in free play opens the current screen blank and stays in free play", async ({ page }) => {
  await page.goto("/#/triage");
  await expect(page.getByTestId("email-input")).not.toHaveValue("");
  await page.keyboard.press("l");
  await expect(page).toHaveURL(/#\/triage\/blank$/);
  await expect(page.getByTestId("email-input")).toHaveValue("");
  await expect(page.getByTestId("guided-bar")).toHaveCount(0);
});

test("the pop-out notes window follows the guided step", async ({ page, context }) => {
  await page.goto("/#/guided/1");
  await expect(page.getByTestId("guided-step")).toHaveText(`1 / ${GUIDED.length}`);
  await page.keyboard.press("n");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.getByTestId("notes-popout").click()]);
  await expect(notes.getByTestId("notes-window")).toContainText(GUIDED[0].note);
  await page.keyboard.press("n");
  await page.keyboard.press("ArrowRight");
  await expect(notes.getByTestId("notes-window")).toContainText(GUIDED[1]?.note ?? "");
});
