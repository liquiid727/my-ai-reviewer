# [RIP-012] Build five-mode JD import UI

Extend the existing JD import dialog to text, file, image, URL, and manual modes through one validated payload interface.

## Acceptance Criteria

- [ ] Use a segmented source-mode control with mutually exclusive, type-appropriate inputs.
- [ ] Validate current-mode input and prevent data from an inactive mode entering the request.
- [ ] Show image/file name, type, size and actionable URL/manual validation.
- [ ] Represent processing/review/duplicate/failure/retry states and stop polling on terminal/ownership loss.
- [ ] Keep Chinese/English resources synchronized and errors localized/safe.
- [ ] Component and desktop/mobile browser checks confirm stable layout and no overlap.

- **Type:** frontend
- **Priority:** high
- **Depends on:** #103, #104
- **SPEC:** RIP-012 sections 8, 9, 11
