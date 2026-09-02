import React from 'react';
import { Box, Button, HStack, Heading, useColorModeValue } from '@chakra-ui/react';
import { HamburgerIcon, CloseIcon } from '@chakra-ui/icons';
import UserProfileMenu from './UserProfileMenu';
import ColorModeToggle from '../../../components/shared/ColorModeToggle';
import type { User } from '../../auth';

interface NavbarProps {
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
    title?: string;
    rightContent?: React.ReactNode;
    user?: User;
    onChangePasswordClick?: () => void;
    onLogoutClick?: () => void;
}

const Navbar: React.FC<NavbarProps> = ({
    isSidebarOpen,
    onToggleSidebar,
    title = 'MRG Labs Graphing Dashboard',
    rightContent,
    user,
    onChangePasswordClick,
    onLogoutClick,
}) => {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.700');
    const hoverBg = useColorModeValue('blue.50', 'blue.900');

    return (
        <Box
            as="nav"
            position="sticky"
            top={0}
            zIndex={1000}
            bg={bgColor}
            borderBottom="1px"
            borderColor={borderColor}
            px={4}
            py={3}
            boxShadow="sm"
        >
            <HStack justify="space-between" align="center">
                <HStack spacing={4}>
                    <Button
                        aria-label={isSidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
                        onClick={onToggleSidebar}
                        variant="ghost"
                        size="md"
                        colorScheme="blue"
                        _hover={{ bg: hoverBg }}
                    >
                        {isSidebarOpen ? <CloseIcon boxSize={3} /> : <HamburgerIcon boxSize={4} />}
                    </Button>
                    <Heading size="md" display={{ base: 'none', md: 'block' }}>
                        {title}
                    </Heading>
                </HStack>

                <HStack spacing={2}>
                    {rightContent && <Box>{rightContent}</Box>}
                    <ColorModeToggle />
                    <UserProfileMenu
                        user={user}
                        onChangePasswordClick={onChangePasswordClick}
                        onLogoutClick={onLogoutClick}
                    />
                </HStack>
            </HStack>
        </Box>
    );
};

export default Navbar;
