{ pkgs ? import <nixpkgs> {}
, lib ? pkgs.lib
, debug ? false
}:

with pkgs.python3Packages;

buildPythonApplication (rec {
  pname = "kisstdlib";
  version = "0.0.1";
  format = "pyproject";

  src = lib.cleanSourceWith {
    src = ./.;
    filter = name: type: let baseName = baseNameOf (toString name); in
      lib.cleanSourceFilter name type
      && (builtins.match ".*.un~" baseName == null)
      && (baseName != "default.nix")
      && (baseName != "dist")
      && (baseName != "result")
      && (baseName != "results")
      && (baseName != "__pycache__")
      && (baseName != ".mypy_cache")
      && (baseName != ".pytest_cache")
      ;
  };

  propagatedBuildInputs = [
    setuptools
    sortedcontainers
  ];
} // lib.optionalAttrs debug {
  nativeBuildInputs = [
    mypy
    pytest
  ];

  preBuild = "find . ; mypy";
  postInstall = "find $out";
})
