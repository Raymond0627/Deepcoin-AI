import * as React from "react";
import Button from "@mui/material/Button";
import { useNavigate } from "react-router-dom";


export default function ButtonUsage() {
  const navigate = useNavigate();
  return (
    <Button
      variant="contained"
      sx={{
        marginTop: "20px", // Add margin top
        backgroundColor: "#0995cc", // Custom blue color
        color: "white", // Text color
        fontSize: "18px", // Increase text size
        padding: "10px 20px", // Add padding
        borderRadius: "8px", // Rounded corners
        "&:hover": {
          backgroundColor: "#0B75C9", // Darker blue on hover
        },
      }}
      onClick={() => navigate("/SecondPage")}
    >
      Start Now
    </Button>
  );
}
