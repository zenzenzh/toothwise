/**
 * ToothWise - IT Expert Evaluation Form (Google Forms builder)
 *
 * Creates the Google Form that IT experts use to evaluate ToothWise, plus a
 * Google Sheet that collects the responses. Run it once:
 *
 *   1. Go to https://script.google.com and click "New project".
 *   2. Delete the sample code, paste this whole file, and click Save.
 *   3. Edit the three settings below if needed.
 *   4. Choose the function "createItExpertForm" and click Run. Allow the
 *      permissions Google asks for (it needs to create a form and a sheet).
 *   5. Open "Execution log": it prints the link to share and the edit link.
 *
 * The statements are the same as the paper's questionnaire (Appendix A,
 * Parts B3 and B), on the same four-point scale, so the answers can be
 * analyzed with paper_build/survey_sections.py together with the earlier
 * responses. Keep the section titles, statement numbers and answer labels
 * unchanged for that to work.
 */

// ---- Settings ---------------------------------------------------------------
var SYSTEM_URL = 'https://toothwise.vercel.app';
// How evaluators get into the staff side. Do not put passwords here: the form
// is shared, so hand out demo accounts separately.
var ACCESS_NOTE = 'The researchers will give you a demo staff account (dentist role) so you can try every feature. ' +
  'Please do not upload real patient photographs; use the sample photographs provided or any non-patient image.';
var RESEARCHERS = 'the ToothWise research team, Universidad de Manila';
// -----------------------------------------------------------------------------

var SCALE = ['Strongly Agree (4)', 'Agree (3)', 'Disagree (2)', 'Strongly Disagree (1)'];

// Section titles must stay exactly as written: the analysis script reads them.
var ISO_SECTIONS = [
  ['1. Security', 'Protection of the system and its data against unauthorized access.', [
    'Only authorized users can log in and access the system\'s functions.',
    'Each role (Dentist, Receptionist, Dental Assistant, Patient) can only access the features permitted for that role.',
    'Passwords and login sessions are handled securely.',
    'Sensitive staff actions are recorded in the audit log for administrative review.']],
  ['2. Privacy', 'Handling of personal and health information.', [
    'Screening images are not publicly exposed and can only be viewed by authorized users.',
    'Patients can only view their own records through the patient portal.',
    'The system handles personal and health information in line with the Data Privacy Act of 2012.']],
  ['3. Usability', 'How easy the system is to learn and use.', [
    'The system is easy to learn and use, even for first-time users.',
    'Navigation between the dashboard, patient records, and screening pages is clear and logical.',
    'Labels, buttons, and messages are easy to understand.',
    'The layout and design of the interface are visually pleasing and organized.']],
  ['4. Reliability', 'How dependably the system works.', [
    'The system runs consistently without unexpected crashes or failures.',
    'When an error occurs, the system shows a clear message and recovers without losing data.',
    'The system produces consistent results when the same image is screened again.']],
  ['5. Performance Efficiency', 'Speed and responsiveness.', [
    'The system analyzes an uploaded image and displays the results within an acceptable time.',
    'Pages and patient records load quickly.',
    'The system remains responsive while performing AI detection.']],
  ['6. Data Protection', 'Accuracy and integrity of stored data.', [
    'Patient, screening, and detection records are stored accurately and completely.',
    'Related records (patients, screenings, findings, recommendations, notes) remain consistent with one another.',
    'The system prevents invalid or incomplete data from being saved.']]
];

var FEATURE_SECTIONS = [
  ['AI Detection and Risk Classification', 'The YOLOv8 and YOLOv12 detection and the computed risk level.', [
    'Toothwise accurately detects tartar, plaque, cavity, gum inflammation, and healthy tooth from a still intraoral photograph.',
    'Combining the YOLOv8 and YOLOv12 outputs produces dependable detection results.',
    'The computed risk score and risk classification (Low, Medium, High) reflect the detected findings appropriately.',
    'The system works well with photos taken using a standard device camera such as a smartphone or webcam.',
    'The detection results are a helpful reference that supports, but does not replace, the dentist\'s judgment.']],
  ['Results Interface and Patient Records', 'The screening results page, patient records, PDF report, and patient portal.', [
    'The bounding boxes and condition labels clearly show where each finding is located on the image.',
    'The plain-language descriptions make the findings easy to understand.',
    'The per-patient record makes it easy to review and compare findings across visits.',
    'The downloadable PDF screening report is complete and useful for clinical recordkeeping.',
    'The self-service patient portal lets patients conveniently view their own screening history and past findings.']],
  ['KNN-Based Personalized Prevention Plan', 'The prevention plan generated after each screening.', [
    'The prevention plan is relevant to the patient\'s detected findings and risk classification.',
    'The recommendations are clear and easy for patients to follow.',
    'The prevention plan encourages earlier preventive action and better oral health awareness.',
    'The prevention plan appropriately serves as guidance and not as a formal medical prescription.']]
];

function addScaleSection(form, section) {
  var title = section[0], help = section[1], statements = section[2];
  form.addGridItem()
    .setTitle(title)
    .setHelpText(help + ' Rate each statement.')
    .setRows(statements.map(function (s, i) { return (i + 1) + '. ' + s; }))
    .setColumns(SCALE)
    .setRequired(true);
}

function createItExpertForm() {
  var form = FormApp.create('ToothWise System Evaluation - IT Experts');
  form.setDescription(
    'ToothWise is an AI-assisted dental screening support system for CodiSmile Dental Clinic. It detects tartar, ' +
    'plaque, cavity, gum inflammation, and healthy tooth in still intraoral photographs using a fused YOLOv8 and ' +
    'YOLOv12 ensemble, computes a risk level, and generates a personalized prevention plan.\n\n' +
    'As an IT expert, you are asked to evaluate the system based on the ISO/IEC 25010 software quality ' +
    'characteristics used in this study and on its main features. It takes about 10 to 15 minutes.\n\n' +
    'This evaluation is conducted by ' + RESEARCHERS + '.');
  form.setProgressBar(true);
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setConfirmationMessage('Thank you for evaluating ToothWise. Your responses have been recorded.');

  // Page 1: consent. "I do not agree" ends the form.
  var consent = form.addMultipleChoiceItem();
  consent.setTitle('Data Privacy Consent')
    .setHelpText('Your answers will be used only for this study and will be reported only as group statistics. ' +
      'Your name is optional and will not appear in the paper. Data are handled in accordance with the Data ' +
      'Privacy Act of 2012 (Republic Act No. 10173). Participation is voluntary, and you may stop at any time.')
    .setRequired(true);

  // Page 2: respondent profile.
  var profile = form.addPageBreakItem().setTitle('Respondent Profile');
  consent.setChoices([
    consent.createChoice('I have read the statement above and agree to take part in this evaluation.', profile),
    consent.createChoice('I do not agree.', FormApp.PageNavigationType.SUBMIT)
  ]);
  form.addTextItem().setTitle('Name (optional)');
  // Keep this answer as is: the analysis script finds IT experts by it.
  form.addMultipleChoiceItem().setTitle('Respondent group')
    .setChoiceValues(['IT expert / IT practitioner']).setRequired(true);
  form.addMultipleChoiceItem().setTitle('Current role')
    .setChoiceValues(['Software developer / engineer', 'Web developer', 'Systems analyst', 'Database administrator',
      'Network or systems administrator', 'Cybersecurity practitioner', 'QA / software tester', 'IT instructor / faculty'])
    .showOtherOption(true).setRequired(true);
  form.addMultipleChoiceItem().setTitle('Years of experience in IT')
    .setChoiceValues(['Less than 1 year', '1 to 3 years', '4 to 6 years', '7 to 10 years', 'More than 10 years'])
    .setRequired(true);

  // Page 3: how to try the system.
  form.addPageBreakItem().setTitle('Before You Answer: Try the System')
    .setHelpText('Open ToothWise at ' + SYSTEM_URL + ' and try it before answering.\n\n' + ACCESS_NOTE + '\n\n' +
      'Suggested steps: sign in on the staff side; add or open a patient; upload a photograph for a new screening ' +
      'and review the detections, risk level, prevention plan, and the image-level evaluation table; switch between ' +
      'the Fused, YOLOv8, and YOLOv12 views; download the PDF report; check the Staff and Audit Log pages; and open ' +
      'the patient portal.\n\nThe first page load may take about a minute while the free server starts.');

  // Page 4: ISO/IEC 25010 quality characteristics.
  form.addPageBreakItem().setTitle('Part I. Software Quality Evaluation (ISO/IEC 25010)')
    .setHelpText('Rate each statement: Strongly Agree (4), Agree (3), Disagree (2), or Strongly Disagree (1).');
  ISO_SECTIONS.forEach(function (s) { addScaleSection(form, s); });

  // Page 5: system features.
  form.addPageBreakItem().setTitle('Part II. System Features')
    .setHelpText('Rate each statement: Strongly Agree (4), Agree (3), Disagree (2), or Strongly Disagree (1).');
  FEATURE_SECTIONS.forEach(function (s) { addScaleSection(form, s); });

  // Page 6: open-ended questions.
  form.addPageBreakItem().setTitle('Part III. Comments and Suggestions');
  form.addParagraphTextItem().setTitle('What did you like most about Toothwise?');
  form.addParagraphTextItem().setTitle('What problems or difficulties did you encounter while using Toothwise?');
  form.addParagraphTextItem().setTitle('What improvements or additional features would you suggest?');

  // Collect responses in a Google Sheet (File > Download > .xlsx for the analysis script).
  var sheet = SpreadsheetApp.create('ToothWise IT Expert Evaluation (Responses)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log('Share this link with IT experts: ' + form.getPublishedUrl());
  Logger.log('Edit the form here: ' + form.getEditUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
}
