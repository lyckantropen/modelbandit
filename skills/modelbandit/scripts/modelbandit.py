# The implementation lives in the modelbandit package beside this file; this
# script stays the invoked entry point, so every doc reference and deployment
# shape keeps working. Running it imports the package and dispatches to main.
if __name__ == "__main__":
    from modelbandit import main
    main()
