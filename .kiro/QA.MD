




QA ISO :
INFO:mcp.server.lowlevel.server:Processing request of type CallToolRequest
INFO:iso_financial_mcp.meta_tools:Fetching 7 data sources for TSM in parallel...
INFO:iso_financial_mcp.datasources.sec_source:SEC filings fetched and cached for TSM: 0 filings
ERROR:iso_financial_mcp.datasources.trends_source:Error in _get_trends_data for TSM: The request failed: Google returned a response with code 429
ERROR:iso_financial_mcp.datasources.trends_source:Error in _fetch_google_trends for TSM: The request failed: Google returned a response with code 429
ERROR:iso_financial_mcp.datasources.trends_source:Error fetching Google Trends for TSM: Failed to fetch trends data: The request failed: Google returned a response with code 429
INFO:iso_financial_mcp.datasources.news_source:News headlines fetched and cached for TSM: 5 articles
WARNING:iso_financial_mcp.datasources.earnings_source:Nasdaq API returned non-iterable rows data for TSM: <class 'NoneType'>
INFO:iso_financial_mcp.datasources.earnings_source:Earnings calendar fetched and cached for TSM: 0 records
INFO:iso_financial_mcp.datasources.finra_source:FINRA short volume fetched and cached for TSM: 1 records
INFO:iso_financial_mcp.meta_tools:No data available for prices for TSM
INFO:iso_financial_mcp.meta_tools:No data available for sec_filings for TSM
INFO:iso_financial_mcp.meta_tools:No data available for earnings for TSM
INFO:iso_financial_mcp.meta_tools:Snapshot complete for TSM: 4 sources, 3 errors
INFO:mcp.server.lowlevel.server:Processing request of type ListToolsRequest
