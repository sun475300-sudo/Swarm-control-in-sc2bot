dnl Autoconf script for the SC2 Zerg Bot portable C/C++ build.
dnl Detects compiler capabilities, required libraries, and SC2 client path.
dnl Run: autoreconf -fi && ./configure && make

AC_PREREQ([2.71])
AC_INIT([sc2_zerg_bot_cpp], [1.0.0], [sc2bot@example.com])
AM_INIT_AUTOMAKE([foreign -Wall -Werror])
AC_CONFIG_SRCDIR([src/combat_sim.cpp])
AC_CONFIG_HEADERS([config.h])

# ── Check for C++20 compiler ─────────────────────────────────────────────────
AC_PROG_CXX
AX_CXX_COMPILE_STDCXX([20], [noext], [mandatory])

# ── Libtool for shared library build ────────────────────────────────────────
LT_INIT

# ── Threading ────────────────────────────────────────────────────────────────
AX_PTHREAD([
    LIBS="$PTHREAD_LIBS $LIBS"
    CFLAGS="$CFLAGS $PTHREAD_CFLAGS"
    CXXFLAGS="$CXXFLAGS $PTHREAD_CFLAGS"
    CC="$PTHREAD_CC"
], [AC_MSG_ERROR([pthreads required but not found])])

# ── Optional: Python 3 for pybind11 bindings ─────────────────────────────────
AC_ARG_WITH([python],
    AS_HELP_STRING([--with-python], [Build Python bindings via pybind11]),
    [with_python=$withval], [with_python=check])

AS_IF([test "x$with_python" != xno], [
    AM_PATH_PYTHON([3.9], [HAVE_PYTHON=yes], [HAVE_PYTHON=no])
    AS_IF([test "x$HAVE_PYTHON" = xyes], [
        AC_DEFINE([HAVE_PYTHON3], [1], [Python 3 is available])
    ])
])
AM_CONDITIONAL([BUILD_PYTHON_BINDINGS], [test "x$HAVE_PYTHON" = xyes])

# ── Check for SQLite3 (battle stats storage) ─────────────────────────────────
PKG_CHECK_MODULES([SQLITE3], [sqlite3 >= 3.36],
    [AC_DEFINE([HAVE_SQLITE3], [1], [SQLite3 available])],
    [AC_MSG_WARN([SQLite3 not found – battle stats DB disabled])])

# ── SC2 client installation path ─────────────────────────────────────────────
AC_ARG_WITH([sc2path],
    AS_HELP_STRING([--with-sc2path=DIR], [Path to StarCraft II installation]),
    [SC2PATH="$withval"], [SC2PATH="$HOME/StarCraftII"])
AC_SUBST([SC2PATH])
AC_DEFINE_UNQUOTED([SC2_DEFAULT_PATH], ["$SC2PATH"], [Default SC2 install path])

AC_CONFIG_FILES([Makefile src/Makefile tests/Makefile])
AC_OUTPUT

AC_MSG_NOTICE([
  SC2 Zerg Bot C++ Module Configuration
  ──────────────────────────────────────
  Compiler    : $CXX
  C++ Std     : C++20
  SC2 Path    : $SC2PATH
  Python bind : ${HAVE_PYTHON:-no}
  SQLite3     : ${SQLITE3_LIBS:-disabled}
])
