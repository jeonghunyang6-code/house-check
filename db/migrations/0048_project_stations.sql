-- H4 역 단위: 철도 사업이 서는 역 중 station 표에 좌표가 있는 역 이름(쉼표). 단지 700m(📖 역세권 p.220) 안이면 그 사업의 역세권
ALTER TABLE transit_projects ADD COLUMN IF NOT EXISTS stations TEXT;
