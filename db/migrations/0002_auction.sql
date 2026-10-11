-- 경매 매각가율 (지표 G6). 출처가 달라도 같은 표에 쌓고 source로 구분한다.
-- 매각가율 = sale_amount / appraisal_of_sold  (매각된 물건의 감정 금액 기준, analytics/auction.py 참고)

CREATE TABLE IF NOT EXISTS court_jurisdiction (
    court_code   TEXT NOT NULL,
    court_name   TEXT NOT NULL,          -- 원천 데이터의 법원명 표기 그대로
    sigungu_code TEXT NOT NULL,          -- 법정동 시군구 코드 5자리
    PRIMARY KEY (court_name, sigungu_code)
);

CREATE TABLE IF NOT EXISTS auction_stats (
    source             TEXT    NOT NULL CHECK (source IN ('kapa', 'ggi_news')),
    period_month       TEXT    NOT NULL CHECK (period_month ~ '^[0-9]{4}-[0-9]{2}$'),
    area_code          TEXT    NOT NULL,                 -- 법원명 또는 시도명
    area_level         TEXT    NOT NULL CHECK (area_level IN ('court', 'sido')),
    use_type           TEXT    NOT NULL,                 -- '아파트' 등
    cases              INTEGER,                          -- 경매 건수
    sold               INTEGER,                          -- 매각 건수
    appraisal_of_sold  BIGINT,                           -- 매각 물건의 감정 금액(원)
    sale_amount        BIGINT,                           -- 매각 금액(원)
    sale_ratio         NUMERIC(6, 4),                    -- 매각가율 (0.8590 = 85.9%)
    sold_ratio         NUMERIC(6, 4),                    -- 매각률
    avg_bidders        NUMERIC(5, 2),
    source_url         TEXT,
    PRIMARY KEY (source, period_month, area_code, use_type)
);

CREATE INDEX IF NOT EXISTS auction_stats_month_idx ON auction_stats (period_month, use_type);
