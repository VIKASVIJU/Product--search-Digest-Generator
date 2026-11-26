import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from scraper import validate_query, discover_websites, scrape_websites_concurrently
from parser import parse_scraped_pages, match_products_across_sites
from digest_generator import filter_and_sort_products, build_comparison_matrix, generate_summary_digest


def render_page(query="", sort_by="price_asc", min_rating="0", only_stock=False, show_digest=False):
    status_html = digest_html = cards_html = matrix_html = ""

    if query:
        ok, msg, params = validate_query(query)
        if not ok:
            status_html = f'<div class="alert error">{html.escape(msg)}</div>'
        else:
            sites = discover_websites(params, "sources.json")
            successes, failures = scrape_websites_concurrently(sites, max_workers=6, timeout=2.0)
            records = parse_scraped_pages(successes, params["tokens"])
            filtered = filter_and_sort_products(
                records,
                max_price=params["max_price"],
                min_rating=float(min_rating or 0),
                only_in_stock=only_stock,
                sort_by=sort_by,
            )
            grouped = match_products_across_sites(filtered)
            matrix = build_comparison_matrix(grouped)

            status_html = (
                f'<div class="alert info">Found {len(sites)} matching website(s); '
                f'scraped {len(successes)} successfully ({len(failures)} unreachable). '
                f'Showing {len(filtered)} product listing(s) across {len(matrix)} unique product(s).</div>'
            )

            if show_digest:
                digest_text = generate_summary_digest(filtered, matrix, failures)
                digest_html = f'<section class="card digest"><h2>Summary Digest (FR9)</h2><p>{html.escape(digest_text)}</p></section>'

            card_items = []
            for r in filtered:
                card_items.append(f"""
                <div class="product-card">
                  <h3>{html.escape(r.title)}</h3>
                  <p class="desc">{html.escape(r.description)}</p>
                  <p><strong>Price:</strong> Rs. {r.price:.0f} | <strong>Rating:</strong> {r.rating} &#9733; ({r.reviews} reviews) | <strong>Availability:</strong> {html.escape(r.availability)}</p>
                  <a href="{html.escape(r.source_url)}" target="_blank" rel="noopener noreferrer">View original page at {html.escape(r.source_name)}</a>
                </div>""")
            cards_html = f'<section><h2>Scraped Products (FR3, FR7, FR10)</h2><div class="grid">{"".join(card_items) or "<p>No matching products.</p>"}</div></section>'

            rows = []
            for item in matrix:
                vendor_cells = "<br>".join(
                    f'{html.escape(o["source_name"])}: Rs. {o["price"]:.0f} ({o["rating"]}&#9733;, {html.escape(o["availability"])})'
                    for o in item["offers"]
                )
                rows.append(f"""
                <tr>
                  <td>{html.escape(item["product_title"])}</td>
                  <td>Rs. {item["lowest_price"]:.0f} ({html.escape(item["lowest_price_vendor"])})</td>
                  <td>{item["highest_rating"]} &#9733; ({html.escape(item["highest_rating_vendor"])})</td>
                  <td>{vendor_cells}</td>
                </tr>""")
            if rows:
                matrix_html = f"""
                <section>
                  <h2>Cross-Site Comparison Matrix (FR4, FR5, FR8)</h2>
                  <table>
                    <thead><tr><th>Product</th><th>Best Price</th><th>Top Rating</th><th>Vendor Breakdown</th></tr></thead>
                    <tbody>{"".join(rows)}</tbody>
                  </table>
                </section>"""

    stock_checked = "checked" if only_stock else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><title>SmartShopper Digest Portal</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Georgia, 'Times New Roman', serif; background: #faf7f2; color: #292524; margin: 0; }}
    .hero {{ background: #7c2d12; color: #fff7ed; padding: 18px 32px; border-bottom: 4px solid #ea580c; }}
    .hero h1 {{ margin: 0; font-size: 24px; }}
    .hero p {{ margin: 4px 0 0; font-size: 13px; color: #fed7aa; font-family: Arial, sans-serif; }}
    .layout {{ display: grid; grid-template-columns: 270px 1fr; gap: 22px; max-width: 1180px; margin: 22px auto; padding: 0 18px; }}
    .sidebar-box {{ background: #ffffff; border: 1px solid #e7e5e4; border-radius: 10px; padding: 16px; height: fit-content; font-family: Arial, sans-serif; }}
    .sidebar-box h3 {{ margin-top: 0; color: #7c2d12; font-size: 15px; border-bottom: 1px solid #e7e5e4; padding-bottom: 8px; }}
    .sidebar-box label.field {{ display: block; font-size: 12px; font-weight: bold; margin: 12px 0 4px; color: #57534e; }}
    .sidebar-box input[type="text"], .sidebar-box select {{ width: 100%; padding: 8px; border: 1px solid #d6d3d1; border-radius: 6px; }}
    .sidebar-box .chk {{ display: block; margin: 12px 0; font-size: 13px; }}
    .sidebar-box button {{ width: 100%; padding: 10px; margin-top: 8px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; background: #ea580c; color: #fff; }}
    .sidebar-box button[value="1"] {{ background: #44403c; }}
    .content {{ font-family: Arial, sans-serif; }}
    .alert {{ padding: 11px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 14px; }}
    .info {{ background: #ffedd5; border-left: 4px solid #ea580c; color: #7c2d12; }}
    .error {{ background: #fee2e2; border-left: 4px solid #dc2626; color: #991b1b; }}
    .digest {{ background: #fefce8; border: 1px solid #eab308; border-left: 5px solid #ca8a04; padding: 14px 16px; border-radius: 8px; margin-bottom: 18px; }}
    .digest h2 {{ margin-top: 0; color: #854d0e; font-size: 17px; }}
    h2 {{ color: #7c2d12; font-size: 18px; }}
    .grid {{ display: flex; flex-direction: column; gap: 10px; }}
    .product-card {{ background: #fff; border: 1px solid #e7e5e4; border-left: 4px solid #ea580c; border-radius: 8px; padding: 12px 16px; }}
    .product-card h3 {{ margin: 0 0 6px; font-size: 16px; color: #1c1917; }}
    .product-card a {{ color: #c2410c; font-weight: bold; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; margin-bottom: 18px; }}
    th, td {{ border: 1px solid #d6d3d1; padding: 9px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #ffedd5; color: #7c2d12; }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>SmartShopper Web Aggregator &amp; Digest Portal</h1>
    <p>Automated Cross-Vendor Product Extraction, Comparison &amp; Summary Synthesis</p>
  </div>
  <div class="layout">
    <aside class="sidebar-box">
      <h3>Search &amp; Filter Controls</h3>
      <form method="GET" action="/">
        <label class="field">Product / Topic Query</label>
        <input type="text" name="q" value="{html.escape(query)}" placeholder="e.g. Running Shoes under 10000" required />
        <label class="field">Sort Order</label>
        <select name="sort">
          <option value="price_asc" {"selected" if sort_by=="price_asc" else ""}>Price: Low to High</option>
          <option value="price_desc" {"selected" if sort_by=="price_desc" else ""}>Price: High to Low</option>
          <option value="rating_desc" {"selected" if sort_by=="rating_desc" else ""}>Customer Rating</option>
          <option value="recommended" {"selected" if sort_by=="recommended" else ""}>Best Value Score</option>
        </select>
        <label class="field">Minimum Rating</label>
        <select name="min_rating">
          <option value="0" {"selected" if min_rating=="0" else ""}>All Ratings</option>
          <option value="4.0" {"selected" if min_rating=="4.0" else ""}>4.0 &#9733; &amp; above</option>
          <option value="4.5" {"selected" if min_rating=="4.5" else ""}>4.5 &#9733; &amp; above</option>
        </select>
        <label class="chk"><input type="checkbox" name="in_stock" value="1" {stock_checked}/> Show In-Stock Only</label>
        <button type="submit" name="digest" value="0">Run Product Search</button>
        <button type="submit" name="digest" value="1">Search + Build Digest</button>
      </form>
    </aside>
    <main class="content">
      {status_html}
      {digest_html}
      {matrix_html}
      {cards_html}
    </main>
  </div>
</body>
</html>"""


class DigestRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        page = render_page(
            query=qs.get("q", [""])[0],
            sort_by=qs.get("sort", ["price_asc"])[0],
            min_rating=qs.get("min_rating", ["0"])[0],
            only_stock=qs.get("in_stock", ["0"])[0] == "1",
            show_digest=qs.get("digest", ["0"])[0] == "1",
        )
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), DigestRequestHandler)
    print("Server running at http://127.0.0.1:8000")
    server.serve_forever()
