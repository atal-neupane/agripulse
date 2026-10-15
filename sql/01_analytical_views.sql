-- AgriPulse analytical views
-- NOTE: The underlying dataset is synthetic.
-- Profitability figures are recorded estimates, not audited net profit.

CREATE OR REPLACE VIEW agripulse.v_farm_profitability AS
WITH farm_revenue AS (
    SELECT
        fi.farm_id,
        SUM(s.total_revenue) AS revenue_npr
    FROM agripulse.sale s
    JOIN agripulse.harvest h
        ON h.harvest_id = s.harvest_id
    JOIN agripulse.planting_cycle pc
        ON pc.cycle_id = h.cycle_id
    JOIN agripulse.field fi
        ON fi.field_id = pc.field_id
    GROUP BY fi.farm_id
),
farm_expenses AS (
    SELECT
        farm_id,
        SUM(amount) AS expenses_npr
    FROM agripulse.farm_expense
    GROUP BY farm_id
)
SELECT
    f.farm_id,
    f.farm_name,
    f.district,
    COALESCE(fr.revenue_npr, 0)::numeric(14,2) AS revenue_npr,
    COALESCE(fe.expenses_npr, 0)::numeric(14,2) AS expenses_npr,
    (
        COALESCE(fr.revenue_npr, 0)
        - COALESCE(fe.expenses_npr, 0)
    )::numeric(14,2) AS recorded_profit_npr
FROM agripulse.farm f
LEFT JOIN farm_revenue fr
    ON fr.farm_id = f.farm_id
LEFT JOIN farm_expenses fe
    ON fe.farm_id = f.farm_id;


CREATE OR REPLACE VIEW agripulse.v_crop_profitability AS
WITH crop_revenue AS (
    SELECT
        pc.crop_id,
        SUM(s.total_revenue) AS revenue_npr,
        SUM(s.quantity_kg) AS sold_kg
    FROM agripulse.sale s
    JOIN agripulse.harvest h
        ON h.harvest_id = s.harvest_id
    JOIN agripulse.planting_cycle pc
        ON pc.cycle_id = h.cycle_id
    GROUP BY pc.crop_id
),
crop_expenses AS (
    SELECT
        pc.crop_id,
        SUM(fe.amount) AS expenses_npr
    FROM agripulse.farm_expense fe
    JOIN agripulse.planting_cycle pc
        ON pc.cycle_id = fe.cycle_id
    GROUP BY pc.crop_id
)
SELECT
    c.crop_id,
    c.crop_name,
    COALESCE(cr.sold_kg, 0)::numeric(14,2) AS sold_kg,
    COALESCE(cr.revenue_npr, 0)::numeric(14,2) AS revenue_npr,
    COALESCE(ce.expenses_npr, 0)::numeric(14,2) AS recorded_expenses_npr,
    (
        COALESCE(cr.revenue_npr, 0)
        - COALESCE(ce.expenses_npr, 0)
    )::numeric(14,2) AS recorded_profit_npr
FROM agripulse.crop c
LEFT JOIN crop_revenue cr
    ON cr.crop_id = c.crop_id
LEFT JOIN crop_expenses ce
    ON ce.crop_id = c.crop_id;


CREATE OR REPLACE VIEW agripulse.v_crop_yield AS
WITH cycle_harvest AS (
    SELECT
        cycle_id,
        SUM(quantity_kg) AS total_harvest_kg
    FROM agripulse.harvest
    GROUP BY cycle_id
),
cycle_yields AS (
    SELECT
        pc.cycle_id,
        pc.crop_id,
        fld.area_hectares,
        ch.total_harvest_kg
    FROM agripulse.planting_cycle pc
    JOIN cycle_harvest ch
        ON ch.cycle_id = pc.cycle_id
    JOIN agripulse.field fld
        ON fld.field_id = pc.field_id
    WHERE fld.area_hectares > 0
)
SELECT
    c.crop_id,
    c.crop_name,
    COUNT(cy.cycle_id) AS harvested_cycles,
    ROUND(SUM(cy.total_harvest_kg)::numeric, 2)
        AS total_harvest_kg,
    ROUND(SUM(cy.area_hectares)::numeric, 2)
        AS total_area_hectares,
    ROUND(
        (SUM(cy.total_harvest_kg)
         / NULLIF(SUM(cy.area_hectares), 0))::numeric,
        2
    ) AS yield_kg_per_hectare
FROM agripulse.crop c
LEFT JOIN cycle_yields cy
    ON cy.crop_id = c.crop_id
GROUP BY c.crop_id, c.crop_name;


CREATE OR REPLACE VIEW agripulse.v_market_price_trends AS
WITH ranked_prices AS (
    SELECT
        mp.crop_id,
        mp.market_name,
        mp.price_date,
        mp.price_per_kg,
        ROW_NUMBER() OVER (
            PARTITION BY mp.crop_id, mp.market_name
            ORDER BY mp.price_date ASC
        ) AS first_rank,
        ROW_NUMBER() OVER (
            PARTITION BY mp.crop_id, mp.market_name
            ORDER BY mp.price_date DESC
        ) AS last_rank
    FROM agripulse.market_price mp
),
price_changes AS (
    SELECT
        crop_id,
        market_name,
        MAX(price_date) FILTER (
            WHERE first_rank = 1
        ) AS first_date,
        MAX(price_per_kg) FILTER (
            WHERE first_rank = 1
        ) AS first_price,
        MAX(price_date) FILTER (
            WHERE last_rank = 1
        ) AS last_date,
        MAX(price_per_kg) FILTER (
            WHERE last_rank = 1
        ) AS last_price
    FROM ranked_prices
    GROUP BY crop_id, market_name
)
SELECT
    c.crop_name,
    pc.market_name,
    pc.first_date,
    ROUND(pc.first_price, 2) AS first_price_npr,
    pc.last_date,
    ROUND(pc.last_price, 2) AS last_price_npr,
    ROUND(pc.last_price - pc.first_price, 2)
        AS price_change_npr,
    ROUND(
        (
            100.0 * (pc.last_price - pc.first_price)
            / NULLIF(pc.first_price, 0)
        )::numeric,
        2
    ) AS price_change_percent
FROM price_changes pc
JOIN agripulse.crop c
    ON c.crop_id = pc.crop_id;
