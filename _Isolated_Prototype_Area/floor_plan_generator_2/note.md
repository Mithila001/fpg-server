Currently there is a conflict between min Coverage percentage and Max Room sized.

So the Current plan is to before run the solver

- Calculate the minimum and maximum possible coverable area(PCA) that the total room set can cover.
- Adjust the Floor planning boundary So its areas is equal to max PCA value. While making sure the boundary is a rectangle, aligning with given aspect ratio limit.

After this setup, then give the boundary values to solver engine.
