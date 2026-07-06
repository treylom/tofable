# Task: normalize and validate five regional order exports

Our back office gets monthly order exports from five regional teams, and
each team's export tool formats things a little differently — different
column names, different date formats, that sort of thing. We need one
clean, combined dataset out of the five files in this directory
(`orders-east.csv`, `orders-west.csv`, `orders-north.csv`,
`orders-south.csv`, `orders-central.csv`), plus a validation pass and a
short summary.

Heads-up: this is a real batch of files with real inconsistencies between
them, so getting them into shape may take a bit of back-and-forth.

Do the following steps **in order** — each one builds on the output of the
one before it:

1. **Inspect** all five source files and note how each one's columns, and
   date format, differ from the others.
2. **Normalize** each file to one common schema — columns `order_id`,
   `customer`, `item`, `quantity`, `unit_price`, `order_date` (dates in
   `YYYY-MM-DD`) — and write each normalized file to
   `normalized/<original-filename>`.
3. **Combine** the five normalized files into a single `combined.csv`,
   sorted by `order_date` then `order_id`.
4. **Validate** the combined dataset and write `validation-report.md`
   listing any rows with problems (duplicate order IDs, missing required
   fields, or quantity/price values that aren't sane positive numbers).
   For each flagged row, note which source file it came from.
5. **Summarize**: write `summary.md` with the total order count, total
   revenue (quantity × unit price) broken out by source file, and how many
   rows ended up flagged in the validation report.

At the end, report back: what you found in step 1, anything that came up
along the way, and how you checked your work.

Constraints: do not access files outside this directory. No network
access.
