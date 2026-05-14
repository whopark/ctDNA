import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'services/case_repository.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final repo = CaseRepository();
  await repo.load();
  runApp(CtdnaApp(repo: repo));
}

class CtdnaApp extends StatelessWidget {
  final CaseRepository repo;
  const CtdnaApp({super.key, required this.repo});

  @override
  Widget build(BuildContext context) {
    final seed = const Color(0xFF1976D2);
    return MaterialApp(
      title: 'ctDNA Lymphoma Viewer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        useMaterial3: true,
        cardTheme: CardTheme(
          elevation: 0.5,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: BorderSide(color: Colors.grey.withOpacity(0.2)),
          ),
        ),
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: HomeScreen(repo: repo),
    );
  }
}
