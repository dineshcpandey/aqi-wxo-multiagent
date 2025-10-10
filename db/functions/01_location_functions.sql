-- DROP FUNCTION gis.get_current_pm25(text, text);

CREATE OR REPLACE FUNCTION gis.get_current_pm25(location_code text, location_level text)
 RETURNS TABLE(code text, location_name text, current_pm25 numeric)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
BEGIN
    -- Normalize input
    location_code := TRIM(location_code);
    location_level := LOWER(TRIM(location_level));

    IF location_code IS NULL OR location_level IS NULL THEN
        RETURN;
    END IF;

    CASE location_level
        WHEN 'district', 'dist' THEN
            RETURN QUERY
            SELECT 
                isd.district_code::text AS code,
                isd.district_name::text AS location_name,
                round(AVG(mthx.pm25_value),2) AS current_pm25
            FROM aq.map_tiles_hotspot_xgb mthx
            JOIN gis.india_districts isd ON ST_Contains(isd.geom, mthx.geom)
            WHERE isd.district_code = location_code
            GROUP BY isd.district_code, isd.district_name;

        WHEN 'sub_district', 'subdistrict', 'sub-dist', 'taluk', 'tehsil' THEN
            RETURN QUERY
            SELECT 
                isd.subdist_code::text AS code,
                isd.subdist_name::text AS location_name,
                round(AVG(mthx.pm25_value),2) AS current_pm25
            FROM aq.map_tiles_hotspot_xgb mthx
            JOIN gis.india_sub_districts isd ON ST_Contains(isd.geom, mthx.geom)
            WHERE isd.subdist_code = location_code
            GROUP BY isd.subdist_code, isd.subdist_name;

        WHEN 'ward' THEN
            RETURN QUERY
            SELECT 
                isd.ward_code::text AS code,
                isd.ward_name::text AS location_name,
                round(AVG(mthx.pm25_value),2) AS current_pm25
            FROM aq.map_tiles_hotspot_xgb mthx
            JOIN gis.india_wards isd ON ST_Contains(ST_SetSRID(isd.geom, 4326), mthx.geom)
            WHERE isd.ward_code = location_code
            GROUP BY isd.ward_code, isd.ward_name;

        WHEN 'state', 'st' THEN
            RETURN QUERY
            SELECT 
                isd.state_code::text AS code,
                isd.state_name::text AS location_name,
                round(AVG(mthx.pm25_value),2) AS current_pm25
            FROM aq.map_tiles_hotspot_xgb mthx
            JOIN gis.india_states isd ON ST_Contains(isd.geom, mthx.geom)
            WHERE isd.state_code = location_code
            GROUP BY isd.state_code, isd.state_name;

        ELSE
            RAISE NOTICE 'Unknown location_level: %', location_level;
            RETURN;
    END CASE;
END;
$function$
;
