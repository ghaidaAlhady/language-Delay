import { describe, expect, it } from "vitest";

import { FollowupDetailPage } from "@/pages/FollowupDetailPage";
import { fixtureFollowup } from "@/tests/fixtures";
import { renderWithProviders, screen } from "@/tests/test-utils";

describe("FollowupDetailPage", () => {
  it("keeps deterministic progress visible and adds the optional summary", async () => {
    renderWithProviders(<FollowupDetailPage />, {
      authenticated: true,
      path: "/followups/:followupId",
      initialEntry: "/followups/followup-1",
    });

    expect(await screen.findByText(fixtureFollowup.comment)).toBeInTheDocument();
    expect(
      screen.getByText(
        (_content, node) =>
          node?.tagName === "P" && Boolean(node.textContent?.includes(fixtureFollowup.next_goal)),
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("صياغة مساندة بالذكاء الاصطناعي")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ملخص تقدم الأسبوع" })).toBeInTheDocument();
  });
});
