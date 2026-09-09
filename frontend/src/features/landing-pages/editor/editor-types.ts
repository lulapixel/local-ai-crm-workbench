export type EditorTab =
  | "content"
  | "services"
  | "social-proof"
  | "visual"
  | "contact"
  | "seo"

export type SaveStatus = "clean" | "dirty" | "saving" | "saved" | "error"

export type EditorValidationErrors = {
  [key: string]: string
}

export type EditorTabItem = {
  id: EditorTab
  label: string
  iconName: string
}
