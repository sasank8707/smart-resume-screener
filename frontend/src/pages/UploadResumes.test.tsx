import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import UploadResumes from "./UploadResumes";

describe("UploadResumes", () => {
  it("rejects unsupported file types client-side with an error toast", async () => {
    const uploadSpy = vi.spyOn(client.api, "uploadResumes");
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <UploadResumes />
      </MemoryRouter>,
    );

    const input = screen.getByTestId("file-input");
    const badFile = new File(["MZ"], "malware.exe", { type: "application/x-msdownload" });
    await user.upload(input as HTMLInputElement, badFile);

    // Nothing queued, no network call made.
    expect(screen.queryByTestId("start-upload")).not.toBeInTheDocument();
    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it("queues a valid file and shows the parse button", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <UploadResumes />
      </MemoryRouter>,
    );
    const input = screen.getByTestId("file-input");
    const txt = new File(["John Doe resume text"], "john.txt", { type: "text/plain" });
    await user.upload(input as HTMLInputElement, txt);
    expect(screen.getByTestId("start-upload")).toBeInTheDocument();
    expect(screen.getByText(/john\.txt/)).toBeInTheDocument();
  });
});
