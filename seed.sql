-- Create the Room Setup Templates table
CREATE TABLE IF NOT EXISTS public.room_setup_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    data JSONB NOT NULL
);

-- Create the Room Size Constraints table
CREATE TABLE IF NOT EXISTS public.room_size_constraints (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    min_w DECIMAL(10,2),
    max_w DECIMAL(10,2),
    min_h DECIMAL(10,2),
    max_h DECIMAL(10,2),
    max_area DECIMAL(10,2),
    min_area DECIMAL(10,2),
    preset_id INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Insert Template
INSERT INTO public.room_setup_templates (name, "data") 
VALUES (
    'Standard 2BHK Layout',
    '[{"id": "livingRoom1", "type": "livingRoom"}, {"id": "bedroom1", "type": "bedroom"}, {"id": "bedroom2", "type": "bedroom"}, {"id": "bathroom1", "type": "bathroom"}, {"id": "kitchen1", "type": "kitchen"}]'
);

-- Insert Constraints
INSERT INTO public.room_size_constraints ("type", min_w, max_w, min_h, max_h, max_area, min_area, preset_id, last_updated) 
VALUES
	 ('bedroom', 10.00, NULL, NULL, NULL, NULL, 97.00, NULL),
	 ('kitchen', 5.00, NULL, NULL, NULL, NULL, 54.00, NULL),
	 ('bathroom', 3.00, NULL, NULL, NULL, NULL, 22.00, NULL),
     ('livingRoom', 3.00, NULL, NULL, NULL, NULL, 60.00, NULL),
	 ('toilet', 3.00, NULL, NULL, NULL, NULL, 16.00, NULL);



CREATE TABLE room_relations_constraints (
    id SERIAL PRIMARY KEY,
    room_type VARCHAR(255) NOT NULL,
    related_room JSONB,
    last_updated DATE DEFAULT CURRENT_DATE
);

INSERT INTO room_relations_constraints (room_type, related_room, last_updated)
VALUES 
    ('bedroom', '["livingRoom"]', CURRENT_DATE),
    ('kitchen', '["livingRoom"]', CURRENT_DATE),
    ('bathroom', '["livingRoom"]', CURRENT_DATE);