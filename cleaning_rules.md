# Cleaning rules for the securities lending tables

Rules 1 to 15 are implemented in `sec_lending_clean_query.txt` (new table, `hermesf_sl_new`),
`sec_lending_clean_query_legacy.txt` (legacy table, `hermesf_sl_legacy`, loaded by `legacy_load.ipynb`)
and `sec_lending_collateral_query.txt`. `sec_lending_union_query.txt` stacks the two loan tables into `hermesf_sl`.
Rules 16 to 18 were tested in `legacy_structure.ipynb` and in the volume plots and are not in any query yet.

## Which rows enter

1. Period. Legacy table from 2021-01-01 to 2026-05-31, new table from 2026-06-01 on.
2. Loan rows only. `tec_ruti` must be present, which removes the net exposure collateral updates
   that carry no UTI. In the legacy table additionally `local_index = 0`, which removes the collateral piece rows.
3. Securities only. `loan_security_id` must be present, which removes commodity loans.
4. Loan value in EUR above zero and below 100 billion.
5. Start date on or before the reference date.
6. Maturity date missing, or on or after the reference date.

## One row per trade and day

7. Rows sharing `tec_ruti` and reference date are one trade. Keep the leg flagged as best value leg.
   Without a flag, keep the lender's leg in the legacy query and the most recently reported leg in the
   new query, where unflagged pairs do not occur.
8. The agent lender is taken from whichever leg reports it.

## Derived fields

9. Side TAKE is the lender, GIVE is the borrower, following the ESMA guidelines on SFTR reporting,
   section 4.12.
10. Country, sector and ultimate parent come from RIAD, with GLEIF as fallback, and for the other
    counterparty the reported country as last fallback.
11. Effective maturity is the termination date if one exists, otherwise the maturity date.
12. Rebate rate is the derived floating rate for floating loans, otherwise the fixed rate.
13. Collateral type in this order. Uncollateralised flag gives `none`. Securities and cash pieces on the
    row give `mixed`, `securities` or `cash`. Then the net exposure flag gives `net_exposure`, a basket
    ID gives `basket`, and the rest is `missing`.
14. Legacy only. Quantity and price notation are derived from which column is filled, `is_opn_term`
    maps to the term type, `uncollsd = 'NORE'` means uncollateralised, and the two collateral flags
    replace the piece counts.
15. Collateral pieces go to a separate table, kept legs only, quantities and cash amounts in absolute
    value, no market values.

## Tested, not yet in any query

16. Bond value correction. For the debt types GOVS, SUNS, FIDE, NFID, LOCA, ABSC and SEPR with a
    price and a value present, the EUR value is rebuilt from the reported inputs instead of trusting
    the reported value:

        value_clean = quantity * factor * (loan_value_eur / loan_value)

    with `factor = price / 10000` for a price of 1000 or more, `price / 100` for a price between 5
    and 1000, and `price` itself below 5. All other security types keep the reported EUR value.

    Why it works. For a bond the quantity is a nominal amount and the price is quoted per 100 of
    nominal, so the value is nominal times price over 100. The reporting errors come from skipping
    that division or from writing the percentage without a decimal point, 10419 for 104.19. A price
    of 1000 or more cannot be a bond price per 100, so it is a percentage times 100. A price between
    5 and 1000 is a percentage. A price below 5 is already a factor such as 0.977 or 1.04. The ratio
    `loan_value_eur / loan_value` is the exchange rate the pipeline applied. Both values carry the
    same error, so the ratio is unaffected by it and only converts the rebuilt value to EUR.
17. Live loans only. The last event lies at most 90 days before the reference date.
18. Cap. The corrected value is at most 10 billion EUR.

## Remarks

Rule 4 becomes redundant once rules 16 and 18 are in. Rule 7 is the one place where the two cleaning
queries differ, harmless today because the new table has no unflagged pairs, but worth aligning when
the queries are touched next.
