import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DataExchangePage from "./DataExchangePage";

const mockListEntities = vi.fn();
const mockPreviewExport = vi.fn();
const mockExportData = vi.fn();
const mockDownloadTemplate = vi.fn();
const mockValidateImport = vi.fn();
const mockImportData = vi.fn();
const mockGenerateReport = vi.fn();

vi.mock("../../services/api", () => ({
  dataExchangeService: {
    listEntities: (...args: unknown[]) => mockListEntities(...args),
    previewExport: (...args: unknown[]) => mockPreviewExport(...args),
    exportData: (...args: unknown[]) => mockExportData(...args),
    downloadTemplate: (...args: unknown[]) => mockDownloadTemplate(...args),
    validateImport: (...args: unknown[]) => mockValidateImport(...args),
    importData: (...args: unknown[]) => mockImportData(...args),
    generateReport: (...args: unknown[]) => mockGenerateReport(...args),
  },
}));

const mockEntities = [
  {
    name: "users",
    display_name: "Users",
    fields: [
      {
        name: "email",
        display_name: "Email",
        field_type: "string",
        exportable: true,
      },
      {
        name: "name",
        display_name: "Name",
        field_type: "string",
        exportable: true,
      },
      { name: "id", display_name: "ID", field_type: "uuid", exportable: false },
    ],
  },
  {
    name: "roles",
    display_name: "Roles",
    fields: [
      {
        name: "name",
        display_name: "Name",
        field_type: "string",
        exportable: true,
      },
    ],
  },
];

const mockPreview = {
  total_count: 10,
  rows: [
    { email: "test@test.com", name: "Test User" },
    { email: "admin@test.com", name: "Admin User" },
  ],
};

async function renderPage() {
  const view = render(
    <MemoryRouter>
      <DataExchangePage />
    </MemoryRouter>,
  );

  await waitFor(() => {
    expect(mockListEntities).toHaveBeenCalled();
  });

  return view;
}

describe("DataExchangePage", () => {
  let createObjectUrlSpy: ReturnType<typeof vi.spyOn>;
  let revokeObjectUrlSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockListEntities.mockResolvedValue(mockEntities);
    mockPreviewExport.mockResolvedValue(mockPreview);
    mockExportData.mockResolvedValue(
      new Blob(["export"], { type: "text/csv" }),
    );
    mockDownloadTemplate.mockResolvedValue(
      new Blob(["template"], { type: "text/csv" }),
    );
    mockValidateImport.mockResolvedValue({
      success: true,
      dry_run: true,
      total_rows: 2,
      inserted: 1,
      updated: 0,
      skipped: 1,
      error_count: 0,
      errors: [],
    });
    mockImportData.mockResolvedValue({
      success: true,
      dry_run: false,
      total_rows: 2,
      inserted: 2,
      updated: 0,
      skipped: 0,
      error_count: 0,
      errors: [],
    });
    mockGenerateReport.mockResolvedValue(
      new Blob(["report"], { type: "application/pdf" }),
    );

    createObjectUrlSpy = vi
      .spyOn(window.URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    revokeObjectUrlSpy = vi
      .spyOn(window.URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    createObjectUrlSpy.mockRestore();
    revokeObjectUrlSpy.mockRestore();
  });

  it("renders page title", async () => {
    await renderPage();
    expect(screen.getByText("data.title")).toBeInTheDocument();
  });

  it("loads entities on mount", async () => {
    await renderPage();
  });

  it("shows entity selector with loaded entities", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("Users")).toBeInTheDocument();
    });
  });

  it("shows export tab by default", async () => {
    await renderPage();
    expect(screen.getByText("data.exportFormat")).toBeInTheDocument();
  });

  it("shows format radio buttons on export tab", async () => {
    await renderPage();
    expect(screen.getByText("csv")).toBeInTheDocument();
    expect(screen.getByText("excel")).toBeInTheDocument();
    expect(screen.getByText("json")).toBeInTheDocument();
  });

  it("shows export preview after loading", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("test@test.com")).toBeInTheDocument();
    });
    expect(screen.getByText("Admin User")).toBeInTheDocument();
  });

  it("shows column selection for exportable fields", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("Email")).toBeInTheDocument();
    });
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("switches to import tab", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.import"));
    expect(screen.getByText("data.downloadTemplate")).toBeInTheDocument();
    expect(screen.getByText("data.importMode")).toBeInTheDocument();
  });

  it("shows import mode options", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.import"));
    expect(screen.getByText("data.mode.insert")).toBeInTheDocument();
    expect(screen.getByText("data.mode.update")).toBeInTheDocument();
    expect(screen.getByText("data.mode.upsert")).toBeInTheDocument();
  });

  it("switches to reports tab", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.reports"));
    expect(screen.getByText("data.reportTitleLabel")).toBeInTheDocument();
    expect(screen.getByText("data.reportFormat")).toBeInTheDocument();
  });

  it("shows error alert and allows dismiss", async () => {
    mockListEntities.mockRejectedValue(new Error("Fail"));
    render(
      <MemoryRouter>
        <DataExchangePage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("data.loadError")).toBeInTheDocument();
    });
  });

  it("shows field count for selected entity", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("3 data.fields")).toBeInTheDocument();
    });
  });

  it("exports selected entity with default columns", async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByRole("button", { name: "data.exportButton" }));

    await waitFor(() => {
      expect(mockExportData).toHaveBeenCalledWith("users", "csv", undefined);
    });
    expect(createObjectUrlSpy).toHaveBeenCalled();
  });

  it("exports with selected columns", async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByText("Email"));
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "data.exportButton" }),
      ).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "data.exportButton" }));

    await waitFor(() => {
      expect(mockExportData).toHaveBeenCalledWith("users", "csv", ["email"]);
    });
  });

  it("downloads template from import tab", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.import"));

    await user.click(
      screen.getByRole("button", { name: "data.downloadTemplateButton" }),
    );

    await waitFor(() => {
      expect(mockDownloadTemplate).toHaveBeenCalledWith("users", "csv");
    });
  });

  it("shows error for invalid import file extension", async () => {
    const user = userEvent.setup({ applyAccept: false });
    await renderPage();
    await user.click(screen.getByText("data.import"));

    const fileInput = document.querySelector(
      "input[type='file']",
    ) as HTMLInputElement;
    const badFile = new File(["content"], "bad.txt", { type: "text/plain" });
    await user.upload(fileInput, badFile);

    await waitFor(() => {
      expect(screen.getByText("data.invalidFileType")).toBeInTheDocument();
    });
  });

  it("validates and imports file successfully", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.import"));

    const fileInput = document.querySelector(
      "input[type='file']",
    ) as HTMLInputElement;
    const csvFile = new File(["email,name\na,b"], "users.csv", {
      type: "text/csv",
    });
    await user.upload(fileInput, csvFile);

    await user.click(
      screen.getByRole("button", { name: "data.validateButton" }),
    );
    await waitFor(() => {
      expect(mockValidateImport).toHaveBeenCalledWith("users", csvFile);
    });

    await user.click(screen.getByRole("button", { name: "data.importButton" }));
    await waitFor(() => {
      expect(mockImportData).toHaveBeenCalledWith("users", csvFile, "upsert");
    });
    expect(screen.getByText("data.dropFileHere")).toBeInTheDocument();
  });

  it("generates report with selected title and format", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(screen.getByText("data.reports"));

    await user.type(screen.getByRole("textbox"), "Users Weekly Report");
    await user.click(
      document.querySelector(
        "input[type='radio'][value='csv']",
      ) as HTMLInputElement,
    );
    await user.click(
      screen.getByRole("button", { name: "data.generateReportButton" }),
    );

    await waitFor(() => {
      expect(mockGenerateReport).toHaveBeenCalledWith("users", {
        title: "Users Weekly Report",
        format: "csv",
        include_summary: true,
      });
    });
  });
});
