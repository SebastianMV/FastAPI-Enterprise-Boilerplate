import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MFASettingsPage from "./MFASettingsPage";

const mockGetStatus = vi.fn();
const mockSetup = vi.fn();
const mockVerify = vi.fn();
const mockDisable = vi.fn();
let mockClipboardWriteText = vi.fn().mockResolvedValue(undefined);

vi.mock("@/services/api", () => ({
  mfaService: {
    getStatus: (...args: unknown[]) => mockGetStatus(...args),
    setup: (...args: unknown[]) => mockSetup(...args),
    verify: (...args: unknown[]) => mockVerify(...args),
    disable: (...args: unknown[]) => mockDisable(...args),
  },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <MFASettingsPage />
    </MemoryRouter>,
  );
}

describe("MFASettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClipboardWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: mockClipboardWriteText },
      configurable: true,
    });
    mockClipboardWriteText.mockResolvedValue(undefined);
  });

  it("shows loading spinner initially", () => {
    mockGetStatus.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows disabled status when MFA is off", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.disabled")).toBeInTheDocument();
    });
    expect(screen.getByText("mfa.inactive")).toBeInTheDocument();
  });

  it("shows enabled status when MFA is on", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: "totp" });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.enabled")).toBeInTheDocument();
    });
    expect(screen.getByText("mfa.active")).toBeInTheDocument();
  });

  it("shows setup button when MFA is disabled", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.beginSetup")).toBeInTheDocument();
    });
  });

  it("starts setup flow on button click", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: "JBSWY3DPEHPK3PXP",
      qr_code: "data:image/png;base64,fake",
      backup_codes: ["code1", "code2", "code3", "code4"],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.beginSetup")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("mfa.beginSetup"));
    await waitFor(() => {
      expect(screen.getByText("mfa.step1Title")).toBeInTheDocument();
    });
    // Secret is hidden by default, click show button to reveal
    fireEvent.click(screen.getByTitle("mfa.showSecret"));
    expect(screen.getByText("JBSWY3DPEHPK3PXP")).toBeInTheDocument();
    expect(screen.getByText("mfa.step2Title")).toBeInTheDocument();
    expect(screen.getByText("mfa.step3Title")).toBeInTheDocument();
  });

  it("shows backup codes on toggle", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: "SECRET",
      qr_code: "data:image/png;base64,fake",
      backup_codes: ["backup1", "backup2"],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.beginSetup")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("mfa.beginSetup"));
    await waitFor(() => {
      expect(screen.getByText("mfa.showCodes")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("mfa.showCodes"));
    expect(screen.getByText("backup1")).toBeInTheDocument();
    expect(screen.getByText("backup2")).toBeInTheDocument();
  });

  it("shows disable button when MFA is enabled", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: "totp" });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.disable2fa")).toBeInTheDocument();
    });
  });

  it("shows disable form on button click", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: "totp" });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.disable2fa")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("mfa.disable2fa"));
    expect(screen.getByText("mfa.current2faCode")).toBeInTheDocument();
    expect(screen.getByText("mfa.password")).toBeInTheDocument();
  });

  it("shows error message on fetch failure", async () => {
    mockGetStatus.mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.fetchError")).toBeInTheDocument();
    });
  });

  it("shows help section", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.aboutTitle")).toBeInTheDocument();
    });
  });

  it("renders back link to profile", async () => {
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("mfa.title")).toBeInTheDocument();
    });
    const backLink = document.querySelector('a[href="/profile"]');
    expect(backLink).toBeInTheDocument();
  });

  it("verifies MFA setup successfully", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: "JBSWY3DPEHPK3PXP",
      qr_code: "data:image/png;base64,fake",
      backup_codes: ["code1", "code2"],
    });
    mockVerify.mockResolvedValue(undefined);

    renderPage();
    await user.click(await screen.findByText("mfa.beginSetup"));
    await user.type(screen.getByPlaceholderText("000000"), "123456");
    await user.click(screen.getByRole("button", { name: "mfa.enable2fa" }));

    await waitFor(() => {
      expect(mockVerify).toHaveBeenCalledWith("123456");
    });
    expect(screen.getByText("mfa.enableSuccess")).toBeInTheDocument();
  });

  it("shows enable error when verification fails", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: "JBSWY3DPEHPK3PXP",
      qr_code: "data:image/png;base64,fake",
      backup_codes: ["code1", "code2"],
    });
    mockVerify.mockRejectedValue(new Error("invalid"));

    renderPage();
    await user.click(await screen.findByText("mfa.beginSetup"));
    await user.type(screen.getByPlaceholderText("000000"), "123456");
    await user.click(screen.getByRole("button", { name: "mfa.enable2fa" }));

    await waitFor(() => {
      expect(screen.getAllByText("mfa.enableError").length).toBeGreaterThan(0);
    });
  });

  it("shows fallback when QR code uri is invalid", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({ is_enabled: false, method: null });
    mockSetup.mockResolvedValue({
      secret: "SECRET",
      qr_code: "not-a-valid-qr-uri",
      backup_codes: ["code1", "code2"],
    });

    renderPage();
    await user.click(await screen.findByText("mfa.beginSetup"));

    expect(screen.getByText("mfa.qrCodeAlt")).toBeInTheDocument();
    expect(screen.queryByAltText("mfa.qrCodeAlt")).not.toBeInTheDocument();
  });

  it("disables MFA successfully", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: "totp" });
    mockDisable.mockResolvedValue(undefined);

    renderPage();
    await user.click(await screen.findByText("mfa.disable2fa"));
    await user.type(screen.getByPlaceholderText("000000"), "654321");
    await user.type(
      document.querySelector("input[type='password']") as HTMLInputElement,
      "Password123!",
    );
    await user.click(
      screen.getByRole("button", { name: "mfa.confirmDisable" }),
    );

    await waitFor(() => {
      expect(mockDisable).toHaveBeenCalledWith("654321", "Password123!");
    });
    expect(screen.getByText("mfa.disableSuccess")).toBeInTheDocument();
  });

  it("shows disable error when disable action fails", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({ is_enabled: true, method: "totp" });
    mockDisable.mockRejectedValue(new Error("fail"));

    renderPage();
    await user.click(await screen.findByText("mfa.disable2fa"));
    await user.type(screen.getByPlaceholderText("000000"), "654321");
    await user.type(
      document.querySelector("input[type='password']") as HTMLInputElement,
      "Password123!",
    );
    await user.click(
      screen.getByRole("button", { name: "mfa.confirmDisable" }),
    );

    await waitFor(() => {
      expect(screen.getByText("mfa.disableError")).toBeInTheDocument();
    });
  });
});
