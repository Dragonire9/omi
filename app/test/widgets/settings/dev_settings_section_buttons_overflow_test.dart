import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:omi/backend/preferences.dart';
import 'package:omi/l10n/app_localizations.dart';
import 'package:omi/pages/settings/developer_mcp_section.dart';
import 'package:omi/pages/settings/widgets/developer_api_keys_section.dart';
import 'package:omi/providers/dev_api_key_provider.dart';
import 'package:omi/providers/mcp_provider.dart';
import 'package:omi/ui/ui.dart';
import 'package:omi/utils/platform/platform_manager.dart';

// Regression test for #19240: Developer settings API and MCP section buttons
// overflowed on narrow viewports (320-375 pt) or at larger text sizes (1.3x)
// when button rows were constrained by an unyielding Row in OmiSectionHeader.
// OmiSectionHeader and the action buttons now wrap gracefully.

Widget _buildHarness({
  required Widget child,
  required double width,
  required Locale locale,
  double textScale = 1.0,
}) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<DevApiKeyProvider>.value(value: DevApiKeyProvider()),
      ChangeNotifierProvider<McpProvider>.value(value: McpProvider()),
    ],
    child: MaterialApp(
      locale: locale,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: MediaQueryData(
          size: Size(width, 900),
          textScaler: TextScaler.linear(textScale),
        ),
        child: Scaffold(
          body: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: child,
          ),
        ),
      ),
    ),
  );
}

void main() {
  setUpAll(() {
    PlatformManager.initializeForLocalHarness();
  });

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await SharedPreferencesUtil.init();
  });

  testWidgets('DeveloperApiKeysSection and DeveloperMcpSection lay out without overflow across widths and locales', (tester) async {
    // Narrow widths and locales reported in #19240 (320 pt, 360 pt, 375 pt in de, fr, en at 1.0x and 1.3x)
    const testWidths = [320.0, 360.0, 375.0];
    const testLocales = [Locale('en'), Locale('de'), Locale('fr')];

    for (final width in testWidths) {
      for (final locale in testLocales) {
        // Test Developer API keys section at 1.0x and 1.3x
        for (final scale in [1.0, 1.3]) {
          await tester.pumpWidget(
            _buildHarness(
              width: width,
              locale: locale,
              textScale: scale,
              child: const DeveloperApiKeysSection(),
            ),
          );
          await tester.pump();

          expect(
            tester.takeException(),
            isNull,
            reason: 'DeveloperApiKeysSection should not overflow at width $width, locale $locale, textScale $scale',
          );
        }

        // Test Developer MCP section at 1.0x and 1.3x
        for (final scale in [1.0, 1.3]) {
          await tester.pumpWidget(
            _buildHarness(
              width: width,
              locale: locale,
              textScale: scale,
              child: const DeveloperMcpSection(),
            ),
          );
          await tester.pump();

          expect(
            tester.takeException(),
            isNull,
            reason: 'DeveloperMcpSection should not overflow at width $width, locale $locale, textScale $scale',
          );
        }
      }
    }
  });
}
