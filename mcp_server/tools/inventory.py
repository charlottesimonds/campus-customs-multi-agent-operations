"""Inventory and pricing tools."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..db import read_connection, rows_to_dicts


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_product_stock_and_pricing(sku: str, size: str | None = None) -> dict:
        """Look up on-hand stock and pricing for a product SKU.

        Returns the quantity and location for each size of the SKU from the
        inventory table (or only the requested size), plus the SKU's unit_cost
        and list_price from the pricing table. Use it to check whether an order
        can be filled from stock and how far a price can move above cost.

        Args:
            sku: Product SKU, e.g. "CC-HOOD-NAVY".
            size: Optional size, e.g. "M" or "OS". Omit to get every size.
        """
        with read_connection() as conn:
            query = "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?"
            params: list = [sku]
            if size is not None:
                query += " AND size = ?"
                params.append(size)
            stock = rows_to_dicts(conn.execute(query, params).fetchall())

            pricing_row = conn.execute(
                "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
            ).fetchone()

        if not stock and pricing_row is None:
            return {"found": False, "message": f"No inventory or pricing records for SKU {sku!r}."}

        result: dict = {"found": True, "sku": sku, "stock": stock}
        if not stock:
            result["stock_message"] = (
                f"No inventory record for SKU {sku!r}"
                + (f" in size {size!r}." if size is not None else ".")
            )
        result["pricing"] = dict(pricing_row) if pricing_row else None
        if pricing_row is None:
            result["pricing_message"] = f"No pricing record for SKU {sku!r}."
        return result

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def evaluate_price_override(sku: str, quantity: int, proposed_unit_price: float) -> dict:
        """Calculate what a requested price (e.g. a bulk discount) would do to revenue and margin.

        Uses the SKU's unit_cost and list_price from the pricing table. Returns
        totals and margins at list price and at the proposed price, the discount
        given up, and below_or_at_cost (true means the shop would lose money or
        break even on every unit). This tool only calculates; it does not
        approve a price. Any price override needs human approval.

        Args:
            sku: Product SKU.
            quantity: Number of units in the order.
            proposed_unit_price: Price per unit being considered.
        """
        if quantity <= 0:
            return {"found": False, "message": "quantity must be a positive whole number."}
        if proposed_unit_price < 0:
            return {"found": False, "message": "proposed_unit_price cannot be negative."}

        with read_connection() as conn:
            row = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            return {"found": False, "message": f"No pricing record for SKU {sku!r}."}

        cost, list_price, price = row["unit_cost"], row["list_price"], proposed_unit_price

        def scenario(unit_price: float) -> dict:
            margin = unit_price - cost
            return {
                "unit_price": round(unit_price, 2),
                "unit_margin": round(margin, 2),
                "margin_pct": round(margin / unit_price * 100, 2) if unit_price else None,
                "order_revenue": round(unit_price * quantity, 2),
                "order_cost": round(cost * quantity, 2),
                "order_margin": round(margin * quantity, 2),
            }

        return {
            "found": True,
            "sku": sku,
            "quantity": quantity,
            "unit_cost": cost,
            "at_list_price": scenario(list_price),
            "at_proposed_price": scenario(price),
            "discount_per_unit": round(list_price - price, 2),
            "discount_pct": round((list_price - price) / list_price * 100, 2),
            "revenue_given_up": round((list_price - price) * quantity, 2),
            "below_or_at_cost": price <= cost,
            "requires_human_approval": True,
        }
