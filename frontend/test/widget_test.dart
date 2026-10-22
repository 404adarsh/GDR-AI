import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:blockbrain_hud/main.dart';
import 'package:blockbrain_hud/state/app_state.dart';

void main() {
  testWidgets('BlockBrainApp initializes without crash', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const BlockBrainApp(),
      ),
    );
    expect(find.text('BLOCKBRAIN'), findsOneWidget);
  });
}
