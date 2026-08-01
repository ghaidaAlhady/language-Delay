import { render, screen } from "@testing-library/react";

import { BackendAvailabilityGate } from "@/app/BackendAvailabilityGate";

describe("BackendAvailabilityGate", () => {
  it("waits for the health endpoint before rendering the application", async () => {
    render(
      <BackendAvailabilityGate>
        <div>التطبيق جاهز</div>
      </BackendAvailabilityGate>,
    );

    expect(
      screen.getByRole("heading", {
        name: /جارٍ تشغيل الخادم/,
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("التطبيق جاهز")).toBeInTheDocument();
  });
});
