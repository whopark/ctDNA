import 'package:flutter/material.dart';

import '../models/case_record.dart';
import '../services/case_repository.dart';
import 'cases_screen.dart';
import 'classifier_screen.dart';
import 'dashboard_screen.dart';
import 'gene_panel_screen.dart';

class HomeScreen extends StatefulWidget {
  final CaseRepository repo;
  const HomeScreen({super.key, required this.repo});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<List<CaseRecord>>(
      stream: widget.repo.stream,
      initialData: widget.repo.cases,
      builder: (context, snap) {
        final cases = snap.data ?? const <CaseRecord>[];
        final screens = <Widget>[
          DashboardScreen(cases: cases),
          CasesScreen(repo: widget.repo),
          const ClassifierScreen(),
          const GenePanelScreen(),
        ];
        return Scaffold(
          body: screens[_index],
          bottomNavigationBar: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (i) => setState(() => _index = i),
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard),
                label: 'Dashboard',
              ),
              NavigationDestination(
                icon: Icon(Icons.folder_outlined),
                selectedIcon: Icon(Icons.folder),
                label: 'Cases',
              ),
              NavigationDestination(
                icon: Icon(Icons.science_outlined),
                selectedIcon: Icon(Icons.science),
                label: 'Classifier',
              ),
              NavigationDestination(
                icon: Icon(Icons.dns_outlined),
                selectedIcon: Icon(Icons.dns),
                label: 'Panels',
              ),
            ],
          ),
        );
      },
    );
  }
}
