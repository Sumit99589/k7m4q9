# Domain research and primary-source register

Research checked 26 October 2026. These references are domain/implementation context, not additional time-series inputs. Historical exchange rules for the January 2026 trading period and the client's internal cutoff still require client confirmation.

## Elexon

1. FUELHH stream specification supplied in the assignment: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
2. WINDFOR stream specification supplied in the assignment: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream
3. WINDFOR dataset documentation: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR
4. Wind forecast documentation: https://bmrs.elexon.co.uk/api-documentation/endpoint/forecast/generation/wind
5. Generation-by-fuel context: https://bmrs.elexon.co.uk/generation-by-fuel-type
6. API and usage introduction: https://bmrs.elexon.co.uk/api-documentation/introduction
7. Operational support for negative wind forecasts, historical change proposal CP1381: https://www.elexon.co.uk/bsc/change-proposal/cp1381/

The documented wind forecast population is operationally visible/metered wind, not a justification for calling this all renewable generation or the utility's contracted wind entitlement. Dataset coverage and comparability need live validation.

The public documentation application needs JavaScript; some details were available in search-indexed documentation rather than a complete rendered schema. The data host and its OpenAPI document could not be reached from the authoring environment. Therefore, adapter tests verify intended behaviour against mocks, **not the live parameter contract or January contents**.

Prepared API calls use base `https://data.elexon.co.uk/bmrs/api/v1` and `/datasets/{WINDFOR|FUELHH}/stream` with `publishDateTimeFrom` and `publishDateTimeTo`. One publication day is fetched at a time. Validate these parameters and response shape against the live service before accepting a real snapshot.

## Day-ahead timing

8. Nord Pool, “About the N2EX Day Ahead Auction”: https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction

The official support page, modified 26 July 2022, describes D+1 physical delivery and 09:50 GMT gate closure. It explicitly points users to current product specifications. That supports next-day interpretation but does not identify the client's venue or prove its January 2026 internal cutoff.

9. EPEX SPOT, trading products: https://www.epexspot.com/en/tradingproducts
10. EPEX SPOT, historical GB auction timing announcement: https://www.epexspot.com/en/news/exchange-council-welcomes-new-timing-gb-day-ahead-auction

Official indexed information references 09:20 GMT for the GB day-ahead auction. Direct access to the current product page was restricted during research. Accordingly, the app does not encode a purported authoritative market gate; 09:00, 09:15 and 09:45 are labelled illustrative desk scenarios. Users can set a different cutoff.

## Software

11. Vercel FastAPI deployment documentation: https://vercel.com/docs/frameworks/backend/fastapi
12. Vercel Python runtime documentation: https://vercel.com/docs/functions/runtimes/python
13. React `createElement`: https://react.dev/reference/react/createElement
14. FastAPI documentation: https://fastapi.tiangolo.com/

Vercel documents a root `app.py` exporting `app` as a supported FastAPI entrypoint, with Python dependency manifests and static serving. This informs the supplied configuration; it is not proof that this project has been deployed. React documents `createElement` as an alternative to JSX, supporting a build-free interface. Local runtime versions and their offline provenance are disclosed separately.

## Unresolved acceptance questions

Confirm the client's decision cutoff and venue; confirm whether the source values represent compatible time averages and wind populations; inspect forecast target granularity and expected publication cadence; determine the desired actual-revision window; agree how much missing coverage is tolerable; and verify redistribution rights before committing real data publicly. No invented answers to these questions were used to manufacture January results.
