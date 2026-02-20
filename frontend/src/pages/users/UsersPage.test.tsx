import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import UsersPage from "./UsersPage";

const mockUsersList = vi.fn();
const mockUsersCreate = vi.fn();
const mockUsersUpdate = vi.fn();
const mockUsersDelete = vi.fn();
const mockRolesList = vi.fn();

vi.mock("@/services/api", () => ({
  usersService: {
    list: (...args: unknown[]) => mockUsersList(...args),
    create: (...args: unknown[]) => mockUsersCreate(...args),
    update: (...args: unknown[]) => mockUsersUpdate(...args),
    delete: (...args: unknown[]) => mockUsersDelete(...args),
  },
  rolesService: {
    list: (...args: unknown[]) => mockRolesList(...args),
  },
}));

vi.mock("@/components/common/Modal", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        {children}
      </div>
    ) : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  AlertModal: ({ isOpen, title, message }: any) =>
    isOpen ? (
      <div data-testid="alert-modal">
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
    ) : null,
}));

const mockUsers = {
  items: [
    {
      id: "u1",
      email: "john@test.com",
      first_name: "John",
      last_name: "Doe",
      is_active: true,
      is_superuser: false,
      roles: ["r1"],
      created_at: "2024-01-15T00:00:00Z",
    },
    {
      id: "u2",
      email: "admin@test.com",
      first_name: "Admin",
      last_name: "User",
      is_active: true,
      is_superuser: true,
      roles: [],
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "u3",
      email: "inactive@test.com",
      first_name: "Inactive",
      last_name: "User",
      is_active: false,
      is_superuser: false,
      roles: [],
      created_at: "2024-03-01T00:00:00Z",
    },
  ],
  total: 3,
};

const mockRoles = {
  items: [
    {
      id: "r1",
      name: "Editor",
      description: "Can edit",
      permissions: [],
      is_system: false,
    },
  ],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsersList.mockResolvedValue(mockUsers);
    mockRolesList.mockResolvedValue(mockRoles);
    mockUsersCreate.mockResolvedValue({ id: "u4" });
    mockUsersUpdate.mockResolvedValue({ id: "u1" });
    mockUsersDelete.mockResolvedValue({});
  });

  it("renders page title", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { name: "users.title" }),
    ).toBeInTheDocument();
  });

  it("shows loading state initially", () => {
    mockUsersList.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    // Loader2 icon is present via animate-spin class
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("displays users after loading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Admin User")).toBeInTheDocument();
  });

  it("shows active/inactive status", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    const activeLabels = screen.getAllByText("users.active");
    const inactiveLabels = screen.getAllByText("users.inactive");
    expect(activeLabels.length).toBeGreaterThanOrEqual(1);
    expect(inactiveLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("filters users by search", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText("users.searchPlaceholder");
    fireEvent.change(searchInput, { target: { value: "admin" } });
    expect(screen.queryByText("John Doe")).not.toBeInTheDocument();
    expect(screen.getByText("Admin User")).toBeInTheDocument();
  });

  it("shows role badges from role data", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Editor")).toBeInTheDocument();
    });
  });

  it("shows administrator badge for superuser", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("settings.administrator")).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("users.addUser"));
    expect(screen.getByTestId("modal")).toBeInTheDocument();
  });

  it("shows error state when query fails", async () => {
    mockUsersList.mockRejectedValue(new Error("Failed"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("users.loadError")).toBeInTheDocument();
    });
  });

  it("shows pagination info", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/users\.showingCount/)).toBeInTheDocument();
    });
  });

  it("shows no users found for empty search", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText("users.searchPlaceholder");
    fireEvent.change(searchInput, { target: { value: "nonexistent" } });
    expect(screen.getByText("users.noUsersFound")).toBeInTheDocument();
  });

  it("creates user from create modal", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    await user.click(screen.getByText("users.addUser"));

    const firstNameInput = screen.getByPlaceholderText(
      "common.placeholderFirstName",
    );
    const lastNameInput = screen.getByPlaceholderText(
      "common.placeholderLastName",
    );
    const emailInput = screen.getByPlaceholderText("common.placeholderEmail");
    const passwordInput = screen.getByPlaceholderText("••••••••");

    await user.type(firstNameInput, "Alice");
    await user.type(lastNameInput, "Smith");
    await user.type(emailInput, "alice@example.com");
    await user.type(passwordInput, "ValidPass1!");

    const submitButtons = screen.getAllByRole("button", {
      name: "users.createUser",
    });
    await user.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(mockUsersCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: "Alice",
          last_name: "Smith",
          email: "alice@example.com",
          password: "ValidPass1!",
        }),
      );
    });
  });

  it("updates selected user from edit modal", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByLabelText("common.edit");
    await user.click(editButtons[0]);

    const firstNameInput = screen.getByDisplayValue("John");
    await user.clear(firstNameInput);
    await user.type(firstNameInput, "Johnny");

    await user.click(screen.getByRole("button", { name: "common.save" }));

    await waitFor(() => {
      expect(mockUsersUpdate).toHaveBeenCalledWith(
        "u1",
        expect.objectContaining({ first_name: "Johnny" }),
      );
    });
  });

  it("deletes selected user from confirm modal", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByLabelText("common.delete");
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId("confirm-modal")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      expect(mockUsersDelete).toHaveBeenCalled();
    });
    expect(mockUsersDelete.mock.calls[0]?.[0]).toBe("u1");
  });
});
