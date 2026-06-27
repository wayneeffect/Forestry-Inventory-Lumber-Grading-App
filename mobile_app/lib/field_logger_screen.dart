import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

class FieldLoggerScreen extends StatefulWidget {
  const FieldLoggerScreen({Key? key}) : super(key: key);

  @override
  _FieldLoggerScreenState createState() => _FieldLoggerScreenState();
}

class _FieldLoggerScreenState extends State<FieldLoggerScreen> {
  final _formKey = GlobalKey<FormState>();
  final _uuid = const Uuid();

  // Automated Metadata States
  String? _recordId;
  DateTime? _timestamp;
  XFile? _capturedImage;
  String _aiSpeciesSuggestion = "Pending Image Capture...";
  double? _latitude;
  double? _longitude;
  bool _isLoadingGps = false;

  // Manual Input Form Controllers / States
  final TextEditingController _dbhController = TextEditingController();
  int _clearFaces = 4; // Default to best quality
  String _assignedGrade = 'Select/Better';

  final List<String> _gradeOptions = [
    'Veneer',
    'Select/Better',
    'No. 1 Common',
    'No. 2 Common',
    'Pallet'
  ];

  @override
  void initState() {
    super.initState();
    _initializeSession();
  }

  // Generate automated transaction keys immediately on screen open
  void _initializeSession() {
    setState(() {
      _recordId = "LOG-${_uuid.v4().substring(0, 8).toUpperCase()}";
      _timestamp = DateTime.now();
    });
  }

  // Core Mechanism: Capture Image & Bind GPS instantly on shutter click
  Future<void> _captureTreeAndLocation() async {
    final ImagePicker picker = ImagePicker();
    
    // 1. Shutter Trigger
    final XFile? photo = await picker.pickImage(source: ImageSource.camera);
    if (photo == null) return;

    setState(() {
      _capturedImage = photo;
      _isLoadingGps = true;
      _aiSpeciesSuggestion = "Analyzing bark profile via Pl@ntNet...";
    });

    // 2. Synchronous GPS Pull
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high
        );
        setState(() {
          _latitude = position.latitude;
          _longitude = position.longitude;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('GPS Telemetry Error: $e')),
      );
    } finally {
      setState(() {
        _isLoadingGps = false;
        // Mocking Pl@ntNet resolution for UI compilation
        _aiSpeciesSuggestion = "Quercus alba (White Oak)"; 
      });
    }
  }

  void _submitLog() {
    if (_formKey.currentState!.validate()) {
      if (_capturedImage == null || _latitude == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('❌ Missing required visual or spatial telemetry.')),
        );
        return;
      }

      // Final structured JSON block ready to ship to your FastAPI backend
      final Map<String, dynamic> backendPayload = {
        "record_id": _recordId,
        "captured_at": _timestamp?.toIso8601String(),
        "image_uri": _capturedImage!.path,
        "ai_species_suggestion": _aiSpeciesSuggestion,
        "latitude": _latitude,
        "longitude": _longitude,
        "estimated_dbh": double.tryParse(_dbhController.text),
        "clear_faces": _clearFaces,
        "assigned_grade": _assignedGrade,
      };

      print("Ready for API: $backendPayload");
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Data Compiled. Syncing with Inventory Server...')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Field Logger & Grader')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // --- SECTION 1: SYSTEM AUTOMATED DATA ---
              Card(
                color: Colors.grey[900],
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Record ID: $_recordId', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text('Timestamp: ${_timestamp?.toLocal().toString()}', style: const TextStyle(color: Colors.grey)),
                      const Divider(color: Colors.grey),
                      Text('Species Match: $_aiSpeciesSuggestion', style: const TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      _isLoadingGps 
                        ? const LinearProgressIndicator()
                        : Text('Telemetry: ${_latitude ?? "0.00000"}, ${_longitude ?? "0.00000"}', style: const TextStyle(color: Colors.amberAccent)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // --- CAMERA ACTION BUTTON ---
              Center(
                child: ElevatedButton.icon(
                  onPressed: _captureTreeAndLocation,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Capture Tree / Log'),
                  style: ElevatedButton.styleFrom(minimumSize: const Size(double.infinity, 50)),
                ),
              ),
              const SizedBox(height: 24),

              // --- SECTION 2: MANUAL DATA ENTRY ---
              const Text('Lumber Grading Inputs', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const Divider(),
              
              // DBH Input Numeric Box
              TextFormField(
                controller: _dbhController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Estimated DBH (Diameter at breast height / inches)',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) return 'Enter DBH measurements.';
                  if (double.tryParse(value) == null) return 'Must be a valid number.';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Clear Faces Count Tracker
              Row(
                mainAxisAlignment: MainAxisAlignment.between,
                children: [
                  const Text('Clear Faces (0-4):', style: TextStyle(fontSize: 16)),
                  DropdownButton<int>(
                    value: _clearFaces,
                    items: [0, 1, 2, 3, 4].map((int value) {
                      return DropdownMenuItem<int>(value: value, child: Text('$value Faces'));
                    }).toList(),
                    onChanged: (val) => setState(() => _clearFaces = val!),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Assigned Grade Selector Dropdown
              DropdownButtonFormField<String>(
                value: _assignedGrade,
                decoration: const InputDecoration(labelText: 'Assigned Structural Grade', border: OutlineInputBorder()),
                items: _gradeOptions.map((String grade) {
                  return DropdownMenuItem<String>(value: grade, child: Text(grade));
                }).toList(),
                onChanged: (val) => setState(() => _assignedGrade = val!),
              ),
              const SizedBox(height: 32),

              // --- TRANSMIT ACTION ---
              ElevatedButton(
                onPressed: _submitLog,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  minimumSize: const Size(double.infinity, 55),
                ),
                child: const Text('Save & Sync Log', style: TextStyle(fontSize: 18, color: Colors.white)),
              )
            ],
          ),
        ),
      ),
    );
  }
}
