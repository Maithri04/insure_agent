-- ============================================================
-- InsureMind AI — PostgreSQL Seed Script
-- Tables: icd_codes, procedure_codes,
--         icd_procedure_mapping, conflict_rules
-- ============================================================

-- ────────────────────────────────────────────
-- CREATE TABLES
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS icd_codes (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10)  UNIQUE NOT NULL,
    description TEXT         NOT NULL,
    category    VARCHAR(100) NOT NULL,
    severity    VARCHAR(20)  NOT NULL CHECK (severity IN ('minor','moderate','serious','critical')),
    is_active   BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS procedure_codes (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(20)  UNIQUE NOT NULL,
    description   TEXT         NOT NULL,
    category      VARCHAR(100) NOT NULL,
    requires_auth BOOLEAN      DEFAULT TRUE,
    is_active     BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS icd_procedure_mapping (
    id             SERIAL PRIMARY KEY,
    icd_code       VARCHAR(10) REFERENCES icd_codes(code)      ON DELETE CASCADE,
    procedure_code VARCHAR(20) REFERENCES procedure_codes(code) ON DELETE CASCADE,
    is_primary     BOOLEAN     DEFAULT TRUE,
    created_at     TIMESTAMP   DEFAULT NOW(),
    UNIQUE (icd_code, procedure_code)
);

CREATE TABLE IF NOT EXISTS conflict_rules (
    id             SERIAL PRIMARY KEY,
    rule_name      VARCHAR(200) NOT NULL,
    icd_code       VARCHAR(10)  REFERENCES icd_codes(code) ON DELETE SET NULL,
    procedure_code VARCHAR(20)  REFERENCES procedure_codes(code) ON DELETE SET NULL,
    conflict_type  VARCHAR(50)  NOT NULL CHECK (
                       conflict_type IN (
                           'contraindication','age_restriction',
                           'gender_restriction','missing_criteria',
                           'duplicate_billing','experimental'
                       )
                   ),
    severity       VARCHAR(20)  NOT NULL CHECK (severity IN ('low','medium','high')),
    description    TEXT         NOT NULL,
    action         VARCHAR(20)  NOT NULL CHECK (action IN ('deny','flag','review')),
    metadata       JSONB,
    is_active      BOOLEAN      DEFAULT TRUE,
    created_at     TIMESTAMP    DEFAULT NOW()
);

-- ────────────────────────────────────────────
-- ICD-10 CODES (100+)
-- ────────────────────────────────────────────

INSERT INTO icd_codes (code, description, category, severity) VALUES

-- Cardiac
('I10',    'Essential (primary) hypertension',                                        'Cardiac',         'moderate'),
('I20.0',  'Unstable angina',                                                          'Cardiac',         'serious'),
('I21.9',  'Acute myocardial infarction, unspecified',                                 'Cardiac',         'critical'),
('I21.01', 'ST elevation MI involving left main coronary artery',                      'Cardiac',         'critical'),
('I21.19', 'ST elevation MI involving other coronary artery',                          'Cardiac',         'critical'),
('I22.0',  'Subsequent ST elevation MI of anterior wall',                              'Cardiac',         'critical'),
('I25.10', 'Atherosclerotic heart disease of native coronary artery without angina',   'Cardiac',         'serious'),
('I48.0',  'Paroxysmal atrial fibrillation',                                           'Cardiac',         'serious'),
('I48.11', 'Longstanding persistent atrial fibrillation',                              'Cardiac',         'serious'),
('I50.9',  'Heart failure, unspecified',                                               'Cardiac',         'serious'),
('I50.22', 'Chronic systolic heart failure',                                           'Cardiac',         'critical'),
('I63.9',  'Cerebral infarction, unspecified',                                         'Cardiac',         'critical'),
('I64',    'Stroke, not specified as haemorrhage or infarction',                       'Cardiac',         'critical'),
('I46.9',  'Cardiac arrest, cause unspecified',                                        'Cardiac',         'critical'),
('I35.0',  'Nonrheumatic aortic valve stenosis',                                       'Cardiac',         'serious'),
('I44.2',  'Atrioventricular block, complete',                                         'Cardiac',         'serious'),
('I71.4',  'Abdominal aortic aneurysm without rupture',                                'Cardiac',         'serious'),
('I82.401','Acute deep vein thrombosis of right femoral vein',                         'Cardiac',         'serious'),
('I26.09', 'Other pulmonary embolism without acute cor pulmonale',                     'Cardiac',         'critical'),

-- Respiratory
('J18.9',  'Pneumonia, unspecified organism',                                          'Respiratory',     'serious'),
('J45.901','Unspecified asthma with (acute) exacerbation',                             'Respiratory',     'moderate'),
('J44.1',  'Chronic obstructive pulmonary disease with acute exacerbation',            'Respiratory',     'serious'),
('J44.0',  'COPD with acute lower respiratory infection',                              'Respiratory',     'serious'),
('J06.9',  'Acute upper respiratory infection, unspecified',                           'Respiratory',     'minor'),
('J02.9',  'Acute pharyngitis, unspecified',                                           'Respiratory',     'minor'),
('J20.9',  'Acute bronchitis, unspecified',                                            'Respiratory',     'moderate'),
('J96.00', 'Acute respiratory failure, unspecified',                                   'Respiratory',     'critical'),
('J12.89', 'Other viral pneumonia',                                                    'Respiratory',     'serious'),
('J85.1',  'Abscess of lung with pneumonia',                                           'Respiratory',     'serious'),
('J38.00', 'Paralysis of vocal cords and larynx, unspecified',                         'Respiratory',     'moderate'),

-- Diabetes & Endocrine
('E11.9',  'Type 2 diabetes mellitus without complications',                           'Endocrine',       'moderate'),
('E11.65', 'Type 2 diabetes mellitus with hyperglycemia',                              'Endocrine',       'moderate'),
('E11.40', 'Type 2 diabetes with diabetic neuropathy, unspecified',                    'Endocrine',       'serious'),
('E11.51', 'Type 2 diabetes with diabetic peripheral angiopathy without gangrene',     'Endocrine',       'serious'),
('E10.9',  'Type 1 diabetes mellitus without complications',                           'Endocrine',       'moderate'),
('E13.9',  'Other specified diabetes mellitus without complications',                  'Endocrine',       'moderate'),
('E05.90', 'Thyrotoxicosis, unspecified, without thyrotoxic crisis',                   'Endocrine',       'moderate'),
('E03.9',  'Hypothyroidism, unspecified',                                              'Endocrine',       'moderate'),
('E66.01', 'Morbid obesity due to excess calories',                                    'Endocrine',       'moderate'),
('E87.1',  'Hypo-osmolality and hyponatraemia',                                        'Endocrine',       'moderate'),

-- Musculoskeletal
('M54.5',  'Low back pain',                                                            'Musculoskeletal', 'minor'),
('M54.4',  'Lumbago with sciatica',                                                    'Musculoskeletal', 'moderate'),
('M17.11', 'Primary osteoarthritis, right knee',                                       'Musculoskeletal', 'moderate'),
('M16.11', 'Primary osteoarthritis, right hip',                                        'Musculoskeletal', 'moderate'),
('M79.3',  'Panniculitis, unspecified',                                                'Musculoskeletal', 'minor'),
('M06.9',  'Rheumatoid arthritis, unspecified',                                        'Musculoskeletal', 'moderate'),
('M32.9',  'Systemic lupus erythematosus, unspecified',                                'Musculoskeletal', 'serious'),
('M80.00', 'Age-related osteoporosis with pathological fracture, unspecified',         'Musculoskeletal', 'serious'),
('M47.816','Spondylosis with radiculopathy, lumbar region',                            'Musculoskeletal', 'moderate'),
('M51.16', 'Intervertebral disc degeneration, lumbar region',                          'Musculoskeletal', 'moderate'),

-- Neurological
('G43.909','Migraine, unspecified, not intractable, without status migrainosus',       'Neurological',    'minor'),
('G35',    'Multiple sclerosis',                                                       'Neurological',    'serious'),
('G20',    'Parkinson disease',                                                        'Neurological',    'serious'),
('G47.00', 'Insomnia, unspecified',                                                    'Neurological',    'minor'),
('G40.909','Epilepsy, unspecified, not intractable, without status epilepticus',       'Neurological',    'moderate'),
('G62.9',  'Polyneuropathy, unspecified',                                              'Neurological',    'moderate'),
('G91.9',  'Hydrocephalus, unspecified',                                               'Neurological',    'serious'),
('G30.9',  'Alzheimer disease, unspecified',                                           'Neurological',    'serious'),
('G06.0',  'Intracranial abscess and granuloma',                                       'Neurological',    'critical'),

-- Gastrointestinal
('K21.0',  'Gastro-oesophageal reflux disease with oesophagitis',                     'Gastrointestinal','minor'),
('K57.30', 'Diverticulosis of large intestine without perforation or abscess',         'Gastrointestinal','moderate'),
('K29.70', 'Gastritis, unspecified, without bleeding',                                 'Gastrointestinal','minor'),
('K92.1',  'Melaena',                                                                  'Gastrointestinal','serious'),
('K35.80', 'Other and unspecified acute appendicitis without abscess',                 'Gastrointestinal','critical'),
('K74.60', 'Unspecified cirrhosis of liver',                                           'Gastrointestinal','serious'),
('K85.90', 'Acute pancreatitis without necrosis or infection, unspecified',            'Gastrointestinal','serious'),
('K25.9',  'Gastric ulcer, unspecified as acute or chronic',                           'Gastrointestinal','moderate'),
('K50.90', 'Crohn disease of small intestine without complications',                   'Gastrointestinal','moderate'),
('K51.90', 'Ulcerative colitis, unspecified, without complications',                   'Gastrointestinal','moderate'),

-- Renal
('N18.3',  'Chronic kidney disease, stage 3 (moderate)',                               'Renal',           'moderate'),
('N18.4',  'Chronic kidney disease, stage 4 (severe)',                                 'Renal',           'serious'),
('N18.5',  'Chronic kidney disease, stage 5',                                          'Renal',           'critical'),
('N17.9',  'Acute kidney failure, unspecified',                                        'Renal',           'critical'),
('N39.0',  'Urinary tract infection, site not specified',                              'Renal',           'minor'),
('N20.0',  'Calculus of kidney',                                                       'Renal',           'moderate'),
('N40.0',  'Benign prostatic hyperplasia without lower urinary tract symptoms',        'Renal',           'moderate'),
('N04.9',  'Nephrotic syndrome with unspecified morphological changes',                'Renal',           'serious'),

-- Oncology
('C34.10', 'Malignant neoplasm of upper lobe of bronchus or lung, unspecified',        'Oncology',        'critical'),
('C50.911','Malignant neoplasm of unspecified site of right female breast',            'Oncology',        'critical'),
('C61',    'Malignant neoplasm of prostate',                                           'Oncology',        'serious'),
('C18.9',  'Malignant neoplasm of colon, unspecified',                                 'Oncology',        'critical'),
('C25.9',  'Malignant neoplasm of pancreas, unspecified',                              'Oncology',        'critical'),
('C71.9',  'Malignant neoplasm of brain, unspecified',                                 'Oncology',        'critical'),
('C80.1',  'Malignant (primary) neoplasm, unspecified',                                'Oncology',        'critical'),
('C91.00', 'Acute lymphoblastic leukaemia not in remission',                           'Oncology',        'critical'),

-- Mental Health
('F32.9',  'Major depressive disorder, single episode, unspecified',                  'Mental Health',   'moderate'),
('F41.1',  'Generalised anxiety disorder',                                             'Mental Health',   'moderate'),
('F43.10', 'Post-traumatic stress disorder, unspecified',                              'Mental Health',   'moderate'),
('F20.9',  'Schizophrenia, unspecified',                                               'Mental Health',   'serious'),
('F31.9',  'Bipolar disorder, unspecified',                                            'Mental Health',   'moderate'),
('F10.20', 'Alcohol dependence, uncomplicated',                                        'Mental Health',   'moderate'),
('F33.0',  'Major depressive disorder, recurrent, mild',                               'Mental Health',   'moderate'),

-- Infectious Disease
('A41.9',  'Sepsis, unspecified organism',                                             'Infectious',      'critical'),
('B20',    'Human immunodeficiency virus disease',                                     'Infectious',      'serious'),
('A09',    'Other and unspecified gastroenteritis and colitis of infectious origin',   'Infectious',      'minor'),
('B18.1',  'Chronic viral hepatitis B without delta-agent',                            'Infectious',      'serious'),
('A15.0',  'Tuberculosis of lung',                                                     'Infectious',      'serious'),

-- ENT
('H66.90', 'Otitis media, unspecified, unspecified ear',                               'ENT',             'minor'),
('J35.01', 'Chronic tonsillitis',                                                      'ENT',             'minor'),
('H81.09', 'Ménière disease, unspecified ear',                                         'ENT',             'moderate'),
('J32.9',  'Chronic sinusitis, unspecified',                                           'ENT',             'minor'),

-- Ophthalmology
('H26.9',  'Unspecified cataract',                                                     'Ophthalmology',   'moderate'),
('H35.30', 'Unspecified macular degeneration',                                         'Ophthalmology',   'serious'),
('H40.10', 'Open-angle glaucoma, unspecified',                                         'Ophthalmology',   'moderate'),
('H43.10', 'Vitreous haemorrhage, unspecified eye',                                    'Ophthalmology',   'serious'),

-- Dermatology
('L40.0',  'Psoriasis vulgaris',                                                       'Dermatology',     'moderate'),
('L20.9',  'Atopic dermatitis, unspecified',                                           'Dermatology',     'minor'),
('L30.9',  'Dermatitis, unspecified',                                                  'Dermatology',     'minor'),
('L89.90', 'Pressure ulcer of unspecified site, unspecified stage',                    'Dermatology',     'serious'),

-- Trauma / Surgical
('S72.001','Fracture of unspecified part of neck of right femur',                      'Trauma',          'serious'),
('S06.0X0','Concussion without loss of consciousness',                                 'Trauma',          'moderate'),
('T14.90', 'Injury, unspecified',                                                      'Trauma',          'moderate'),
('S52.501','Unspecified fracture of lower end of right radius',                        'Trauma',          'moderate'),

-- Obstetric/Gynaecology
('O42.00', 'Preterm premature rupture of membranes, unspecified',                      'Obstetrics',      'serious'),
('O20.0',  'Threatened abortion',                                                      'Obstetrics',      'moderate'),
('N80.0',  'Endometriosis of uterus',                                                  'Gynaecology',     'moderate'),

-- Paediatric
('P07.30', 'Preterm newborn, unspecified weeks of gestation',                          'Paediatric',      'critical'),
('J21.9',  'Acute bronchiolitis, unspecified',                                         'Paediatric',      'moderate'),
('G80.9',  'Cerebral palsy, unspecified',                                              'Paediatric',      'serious')

ON CONFLICT (code) DO NOTHING;


-- ────────────────────────────────────────────
-- PROCEDURE CODES
-- ────────────────────────────────────────────

INSERT INTO procedure_codes (code, description, category, requires_auth) VALUES
('99213',  'Office or outpatient visit, established patient, moderate complexity',          'Evaluation',       FALSE),
('99214',  'Office or outpatient visit, established patient, moderate-high complexity',     'Evaluation',       FALSE),
('99223',  'Initial hospital care, high complexity',                                        'Evaluation',       TRUE),
('99233',  'Subsequent hospital care, high complexity',                                     'Evaluation',       TRUE),

-- Cardiac Procedures
('93000',  'Electrocardiogram, routine ECG with at least 12 leads',                         'Cardiac',          FALSE),
('93306',  'Echocardiography transthoracic, complete',                                      'Cardiac',          TRUE),
('93510',  'Left heart catheterization',                                                    'Cardiac',          TRUE),
('92928',  'Percutaneous coronary angioplasty (PTCA)',                                      'Cardiac',          TRUE),
('33533',  'Coronary artery bypass graft (CABG) using arterial graft',                      'Cardiac',          TRUE),
('33249',  'Implantable cardioverter-defibrillator (ICD) insertion',                        'Cardiac',          TRUE),
('93571',  'Coronary angiography',                                                          'Cardiac',          TRUE),
('33208',  'Permanent pacemaker insertion',                                                 'Cardiac',          TRUE),

-- Orthopaedic / Surgical
('27447',  'Total knee arthroplasty',                                                       'Orthopaedic',      TRUE),
('27130',  'Total hip arthroplasty',                                                        'Orthopaedic',      TRUE),
('22612',  'Lumbar spinal fusion',                                                          'Orthopaedic',      TRUE),
('29881',  'Arthroscopy knee, surgical; with meniscectomy',                                 'Orthopaedic',      TRUE),
('27759',  'Open treatment of tibial shaft fracture',                                       'Orthopaedic',      TRUE),

-- General Surgery
('47562',  'Laparoscopic cholecystectomy',                                                  'General Surgery',  TRUE),
('44950',  'Appendectomy',                                                                  'General Surgery',  TRUE),
('49505',  'Repair of inguinal hernia',                                                     'General Surgery',  TRUE),
('43239',  'Esophagogastroduodenoscopy (EGD) with biopsy',                                  'General Surgery',  TRUE),
('45378',  'Colonoscopy, diagnostic',                                                       'General Surgery',  TRUE),
('45380',  'Colonoscopy with biopsy',                                                       'General Surgery',  TRUE),

-- Neurosurgery
('61510',  'Craniotomy for excision of brain tumor',                                        'Neurosurgery',     TRUE),
('63030',  'Laminotomy with discectomy, lumbar',                                            'Neurosurgery',     TRUE),
('61070',  'Puncture of shunt tubing for aspiration',                                       'Neurosurgery',     TRUE),

-- Oncology
('96413',  'Chemotherapy administration intravenous, first hour',                           'Oncology',         TRUE),
('77301',  'Intensity modulated radiation therapy (IMRT) planning',                         'Oncology',         TRUE),
('38230',  'Bone marrow harvesting for transplantation',                                    'Oncology',         TRUE),

-- Imaging
('71046',  'Radiologic examination, chest; 2 views',                                        'Imaging',          FALSE),
('74177',  'CT scan of abdomen and pelvis with contrast',                                   'Imaging',          TRUE),
('70553',  'MRI brain without and with contrast',                                           'Imaging',          TRUE),
('78816',  'PET scan, skull base to mid-thigh',                                             'Imaging',          TRUE),
('93351',  'Echocardiography with stress testing',                                          'Imaging',          TRUE),

-- Renal
('90935',  'Hemodialysis procedure',                                                        'Renal',            TRUE),
('50590',  'Lithotripsy (ESWL) of kidney stone',                                            'Renal',            TRUE),
('50543',  'Laparoscopic partial nephrectomy',                                              'Renal',            TRUE),

-- Ophthalmology
('66984',  'Extracapsular cataract extraction with IOL implant',                            'Ophthalmology',    TRUE),
('67028',  'Intravitreal injection of therapeutic agent',                                   'Ophthalmology',    TRUE),

-- Respiratory
('94010',  'Spirometry',                                                                    'Respiratory',      FALSE),
('31622',  'Bronchoscopy, diagnostic',                                                      'Respiratory',      TRUE),
('32663',  'Thoracoscopy (VATS) with lobectomy',                                            'Respiratory',      TRUE),

-- Mental Health
('90837',  'Psychotherapy, 60 minutes',                                                     'Mental Health',    FALSE),
('90853',  'Group psychotherapy',                                                           'Mental Health',    FALSE),

-- Obstetric / Gynaecology
('59510',  'Routine obstetric care, cesarean delivery',                                     'Obstetrics',       TRUE),
('58150',  'Total abdominal hysterectomy',                                                  'Gynaecology',      TRUE),
('58661',  'Laparoscopic removal of adnexal structures',                                    'Gynaecology',      TRUE)

ON CONFLICT (code) DO NOTHING;


-- ────────────────────────────────────────────
-- ICD → PROCEDURE MAPPINGS
-- ────────────────────────────────────────────

INSERT INTO icd_procedure_mapping (icd_code, procedure_code, is_primary) VALUES
-- Cardiac
('I21.9',  '93571', TRUE),
('I21.9',  '92928', FALSE),
('I21.01', '33533', TRUE),
('I21.01', '92928', FALSE),
('I25.10', '93571', TRUE),
('I25.10', '92928', FALSE),
('I25.10', '33533', FALSE),
('I48.0',  '93000', TRUE),
('I48.0',  '93306', FALSE),
('I48.11', '33249', TRUE),
('I50.9',  '93306', TRUE),
('I50.22', '33249', TRUE),
('I35.0',  '33533', TRUE),
('I44.2',  '33208', TRUE),
('I71.4',  '33533', TRUE),
('I82.401','93571', TRUE),
('I26.09', '93571', TRUE),
('I10',    '93000', TRUE),
('I10',    '99213', FALSE),
-- Respiratory
('J18.9',  '71046', TRUE),
('J18.9',  '94010', FALSE),
('J44.1',  '94010', TRUE),
('J44.0',  '31622', TRUE),
('J96.00', '31622', TRUE),
('J45.901','94010', TRUE),
('C34.10', '32663', TRUE),
('C34.10', '78816', FALSE),
-- Musculoskeletal
('M17.11', '27447', TRUE),
('M17.11', '29881', FALSE),
('M16.11', '27130', TRUE),
('M54.5',  '99213', TRUE),
('M54.4',  '99213', TRUE),
('M47.816','22612', TRUE),
('M51.16', '63030', TRUE),
('M80.00', '99223', TRUE),
-- Gastrointestinal
('K35.80', '44950', TRUE),
('K21.0',  '43239', TRUE),
('K74.60', '45378', TRUE),
('K85.90', '99223', TRUE),
('K92.1',  '45380', TRUE),
('K25.9',  '43239', TRUE),
('K50.90', '45378', TRUE),
('K51.90', '45378', TRUE),
-- Renal
('N18.3',  '99213', TRUE),
('N18.4',  '90935', TRUE),
('N18.5',  '90935', TRUE),
('N17.9',  '90935', TRUE),
('N20.0',  '50590', TRUE),
('N40.0',  '99213', TRUE),
-- Oncology
('C50.911','96413', TRUE),
('C50.911','77301', FALSE),
('C61',    '96413', TRUE),
('C18.9',  '96413', TRUE),
('C25.9',  '96413', TRUE),
('C71.9',  '61510', TRUE),
('C71.9',  '70553', FALSE),
('C91.00', '38230', TRUE),
-- Neurological
('G35',    '70553', TRUE),
('G20',    '99213', TRUE),
('G40.909','99213', TRUE),
('G30.9',  '70553', TRUE),
('G91.9',  '61070', TRUE),
-- Ophthalmology
('H26.9',  '66984', TRUE),
('H35.30', '67028', TRUE),
('H43.10', '67028', TRUE),
-- Mental Health
('F32.9',  '90837', TRUE),
('F41.1',  '90837', TRUE),
('F20.9',  '90837', TRUE),
('F43.10', '90837', TRUE),
-- Diabetes
('E11.9',  '99213', TRUE),
('E11.40', '99214', TRUE),
('E11.51', '99223', TRUE),
-- Obstetrics
('O42.00', '59510', TRUE),
('N80.0',  '58661', TRUE)

ON CONFLICT (icd_code, procedure_code) DO NOTHING;


-- ────────────────────────────────────────────
-- CONFLICT RULES
-- ────────────────────────────────────────────

INSERT INTO conflict_rules (rule_name, icd_code, procedure_code, conflict_type, severity, description, action, metadata) VALUES

-- Age Restrictions
('Pediatric CABG Restriction',        'I25.10', '33533', 'age_restriction',    'high',   'CABG is not indicated for patients under 18. Pediatric cardiac surgery requires specialized protocol.',                                               'deny',   '{"min_age": 0, "max_age": 17}'),
('Knee Replacement Age Minimum',      'M17.11', '27447', 'age_restriction',    'medium', 'Total knee arthroplasty is generally not recommended for patients under 30 without exhausting conservative treatments.',                              'review', '{"min_age": 0, "max_age": 29}'),
('Hip Replacement Age Minimum',       'M16.11', '27130', 'age_restriction',    'medium', 'Total hip arthroplasty for patients under 30 requires special authorization and documentation of failed conservative management.',                    'review', '{"min_age": 0, "max_age": 29}'),
('ICD Implant Age Restriction',       'I50.22', '33249', 'age_restriction',    'high',   'ICD implantation in patients under 18 requires pediatric electrophysiology specialist evaluation.',                                                   'review', '{"min_age": 0, "max_age": 17}'),
('Dialysis Initiation Age Review',    'N18.5',  '90935', 'age_restriction',    'medium', 'Initiating dialysis in patients under 16 requires nephrology specialist approval and parental consent documentation.',                               'review', '{"min_age": 0, "max_age": 15}'),

-- Gender Restrictions
('Prostate Cancer — Female Patient',  'C61',    '96413', 'gender_restriction', 'high',   'ICD C61 (prostate cancer) cannot be billed for female patients. Verify diagnosis coding accuracy.',                                                  'deny',   '{"allowed_genders": ["male"]}'),
('Hysterectomy — Male Patient',       NULL,     '58150', 'gender_restriction', 'high',   'Total abdominal hysterectomy (58150) is not applicable for male patients.',                                                                           'deny',   '{"allowed_genders": ["female"]}'),
('Ovarian Surgery — Male Patient',    NULL,     '58661', 'gender_restriction', 'high',   'Laparoscopic removal of adnexal structures is not applicable for male patients.',                                                                     'deny',   '{"allowed_genders": ["female"]}'),
('C-Section — Male Patient',          'O42.00', '59510', 'gender_restriction', 'high',   'Obstetric delivery procedures cannot be billed for male patients. Verify patient gender and diagnosis.',                                              'deny',   '{"allowed_genders": ["female"]}'),

-- Clinical Contraindications
('CABG Without Cardiac Diagnosis',    NULL,     '33533', 'contraindication',   'high',   'Coronary artery bypass graft requires documented cardiac diagnosis (CAD, angina, or MI). Submit supporting documentation.',                          'flag',   NULL),
('Chemotherapy Without Cancer Dx',    NULL,     '96413', 'contraindication',   'high',   'Chemotherapy administration requires a confirmed malignancy diagnosis. Provide oncology workup and histopathology report.',                          'deny',   NULL),
('Craniotomy Without Brain Dx',       NULL,     '61510', 'contraindication',   'high',   'Craniotomy for tumor excision requires documented intracranial pathology confirmed by MRI/CT.',                                                       'deny',   NULL),
('ICD Implant Requires HF/Arrhythmia',NULL,     '33249', 'missing_criteria',   'high',   'ICD implantation requires documented heart failure (EF ≤35%) or documented lethal arrhythmia. Submit cardiology report and echo results.',          'flag',   NULL),
('Bone Marrow Transplant Criteria',   NULL,     '38230', 'missing_criteria',   'high',   'Bone marrow transplant requires documented hematologic malignancy, HLA matching results, and transplant center approval.',                           'deny',   NULL),
('PTCA Requires Angiography',         'I21.9',  '92928', 'missing_criteria',   'medium', 'Percutaneous coronary angioplasty should be preceded by documented coronary angiography results.',                                                   'flag',   NULL),
('Spinal Fusion — Conservative Req',  'M47.816','22612', 'missing_criteria',   'medium', 'Lumbar spinal fusion requires documented failure of conservative treatment (≥6 weeks physiotherapy, medications) before authorization.',              'review', NULL),
('Dialysis Requires Stage 5 CKD',     'N18.3',  '90935', 'contraindication',   'high',   'Hemodialysis initiation is not indicated for Stage 3 CKD. Typically reserved for Stage 4/5 or AKI. Submit nephrology consultation note.',           'deny',   NULL),
('PET Scan — Cancer Required',        NULL,     '78816', 'missing_criteria',   'medium', 'PET scan authorization requires documented malignancy or high clinical suspicion with supporting imaging/biopsy.',                                    'flag',   NULL),
('Colonoscopy Frequency Limit',       'K50.90', '45378', 'contraindication',   'low',    'Colonoscopy should not be repeated within 12 months unless clinically justified. Provide prior procedure date and indication.',                       'review', NULL),

-- Experimental / Investigational
('Experimental Oncology Therapy',     'C80.1',  '96413', 'experimental',       'medium', 'Chemotherapy for unspecified malignancy requires tumor board review and documented treatment protocol for authorization.',                           'review', NULL),
('IMRT Requires Radiation Oncologist',NULL,     '77301', 'missing_criteria',   'medium', 'IMRT planning requires documented review by a board-certified radiation oncologist. Submit treatment plan.',                                         'flag',   NULL),

-- Duplicate Billing Prevention
('Duplicate Echo Billing',            'I50.9',  '93306', 'duplicate_billing',  'low',    'Echocardiography billed within 90 days may require justification for repeat study. Document clinical change from previous study.',                   'review', NULL)

ON CONFLICT DO NOTHING;

-- ────────────────────────────────────────────
-- INDEXES for performance
-- ────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_icd_codes_code        ON icd_codes (code);
CREATE INDEX IF NOT EXISTS idx_icd_codes_severity    ON icd_codes (severity);
CREATE INDEX IF NOT EXISTS idx_procedure_codes_code  ON procedure_codes (code);
CREATE INDEX IF NOT EXISTS idx_icd_proc_mapping_icd  ON icd_procedure_mapping (icd_code);
CREATE INDEX IF NOT EXISTS idx_conflict_rules_icd    ON conflict_rules (icd_code);
CREATE INDEX IF NOT EXISTS idx_conflict_rules_proc   ON conflict_rules (procedure_code);