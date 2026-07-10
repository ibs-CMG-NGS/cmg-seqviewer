"""
Qt-independent plot rendering functions (single source of truth).

각 플롯 타입의 순수 렌더 함수 `render_{type}(ax, df, params)`를 모아둔다. 화면 다이얼로그
(`_do_plot`/`_draw_plot`)와 재현 번들 스크립트가 **동일한 함수**를 사용해, 코드 중복과
drift를 방지한다 (BUNDLE_EXPORT_IMPLEMENTATION.md §3.5 Level 2(b)).

규약:
  - 의존성은 matplotlib / pandas / numpy 만 (Qt·다이얼로그 참조 금지).
  - params 는 해당 다이얼로그의 get_plot_params() 와 동일 키.
  - 번들 export는 inspect.getsource() 로 함수 소스를 스크립트에 inline 한다.
"""
