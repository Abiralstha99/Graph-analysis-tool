import React from 'react';
import {
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    MenuDivider,
    Avatar,
    Box,
    Text,
    VStack,
    useColorModeValue,
    IconButton,
    Icon,
} from '@chakra-ui/react';
import { FaUserCircle } from 'react-icons/fa';
import type { User } from '../../auth';
import UserBackground from './UserBackground';

interface UserProfileMenuProps {
    user?: User | null;
    onChangePasswordClick?: () => void;
    onLogoutClick?: () => void;
}

const UserProfileMenu: React.FC<UserProfileMenuProps> = ({
    user,
    onChangePasswordClick = () => console.log('Change Password clicked'),
    onLogoutClick = () => console.log('Logout clicked'),
}) => {
    const menuBg = useColorModeValue('white', 'gray.800');
    const menuBorder = useColorModeValue('gray.200', 'gray.600');
    const hoverBg = useColorModeValue('blue.50', 'blue.900');
    const textColor = useColorModeValue('gray.800', 'gray.100');
    const subtleTextColor = useColorModeValue('gray.600', 'gray.400');

    return (
        <Menu>
            {({ isOpen }) => (
                <>
                    <MenuButton
                        as={IconButton}
                        aria-label="User menu"
                        icon={
                            <Icon
                                as={FaUserCircle}
                                w="32px"
                                h="32px"
                                color="gray.600"
                                cursor="pointer"
                                transition="all 0.2s"
                                _hover={{
                                    transform: 'scale(1.05)',
                                    color: 'gray.700',
                                }}
                            />
                        }
                        variant="ghost"
                        _hover={{ bg: 'transparent' }}
                        _active={{ bg: 'transparent' }}
                    />
                    <MenuList
                        bg={menuBg}
                        borderColor={menuBorder}
                        boxShadow="xl"
                        py={2}
                        minW="240px"
                        motionProps={{
                            variants: {
                                enter: {
                                    opacity: 1,
                                    y: 0,
                                    scale: 1,
                                    transition: {
                                        duration: 0.2,
                                        ease: [0.4, 0, 0.2, 1],
                                    },
                                },
                                exit: {
                                    opacity: 0,
                                    y: -8,
                                    scale: 0.95,
                                    transition: {
                                        duration: 0.15,
                                        ease: [0.4, 0, 1, 1],
                                    },
                                },
                            },
                        }}
                    >
                        {/* User Info Section */}
                        <Box px={4} py={3} cursor="default">
                            <VStack align="start" spacing={0}>
                                <Text
                                    fontWeight="semibold"
                                    fontSize="sm"
                                    color={textColor}
                                >
                                    {user?.username || 'Guest User'}
                                </Text>
                                <Text
                                    fontSize="xs"
                                    color={subtleTextColor}
                                    noOfLines={1}
                                >
                                    Welcome!
                                </Text>
                            </VStack>
                        </Box>

                        <MenuDivider my={1} />

                        {/* Menu Items */}
                        <MenuItem
                            onClick={onChangePasswordClick}
                            _hover={{ bg: hoverBg }}
                            borderRadius="md"
                            mx={2}
                            fontSize="sm"
                            transition="all 0.2s"
                        >
                            Change Password
                        </MenuItem>
                        <MenuItem
                            onClick={onLogoutClick}
                            _hover={{ bg: 'red.50', color: 'red.600' }}
                            borderRadius="md"
                            mx={2}
                            fontSize="sm"
                            transition="all 0.2s"
                            color="red.500"
                            fontWeight="medium"
                        >
                            Logout
                        </MenuItem>
                    </MenuList>
                </>
            )}
        </Menu>
    );
};

export default UserProfileMenu;
